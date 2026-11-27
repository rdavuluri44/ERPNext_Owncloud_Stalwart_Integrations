// Companion UI only. Authentik remains the authority for sessions, permissions,
// invitations, mail delivery and the existing closed enrollment flow.
export const FLOW_SLUG = "cloud-first-time-enrollment";
export const RECOVERY_FLOW_SLUG = "cloud-passkey-recovery-invitation";
export const APPROVAL_GROUP = "Workspace Users";
export const EXPIRY_HOURS = Object.freeze([1, 6, 12, 24, 48, 72]);
// P78: how many times the link may be opened; a successful setup ends it earlier.
export const ATTEMPTS = Object.freeze([1, 2, 3, 4, 5]);
export const DEFAULT_ATTEMPTS = 5;
const API_ROOT = "/api/v3/";
const INVITATIONS = "stages/invitation/invitations/";

export class InvitationError extends Error {}

export function csrfCookie(cookie) {
  const match = cookie.split(";").map((v) => v.trim()).find((v) => v.startsWith("authentik_csrf="));
  return match ? decodeURIComponent(match.slice("authentik_csrf=".length)) : "";
}

export function approved(user, groupName = APPROVAL_GROUP) {
  return user.is_active === true && ["internal", "external"].includes(user.type)
    && Array.isArray(user.groups_obj)
    && user.groups_obj.some((group) => group.name === groupName)
    && typeof user.email === "string" && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(user.email)
    && user.email === user.email.trim();
}

function duplicateEmail(users, email) {
  return users.filter((user) => user.is_active === true
    && user.email?.trim().toLowerCase() === email.trim().toLowerCase()).length !== 1;
}

export function invitationKind(user, hasPasskey) {
  const verified = user.attributes?.cloud_verified_email === user.email
    || user.attributes?.google_verified_email === user.email;
  return hasPasskey || Boolean(user.last_login) || verified ? "recovery" : "enrollment";
}

export class InvitationClient {
  constructor({ fetcher = (...args) => globalThis.fetch(...args), cookie = () => document.cookie, test = false,
    origin = () => location.origin, now = () => Date.now(), uuid = () => crypto.randomUUID(),
    attemptsAvailable = false } = {}) {
    Object.assign(this, { fetcher, cookie, origin, now, uuid, test, attemptsAvailable });
    this.busy = false;
  }

  async api(path, { method = "GET", data } = {}) {
    const url = new URL(path.startsWith(API_ROOT) ? path : API_ROOT + path, this.origin());
    if (url.origin !== this.origin() || !url.pathname.startsWith(API_ROOT)) {
      throw new InvitationError("Unexpected API address. No request was made.");
    }
    const headers = { Accept: "application/json" };
    if (method !== "GET") {
      const csrf = csrfCookie(this.cookie());
      if (!csrf) throw new InvitationError("Your session needs refreshing. Open Authentik administration, then reload this page.");
      headers["X-authentik-CSRF"] = csrf;
      headers["Content-Type"] = "application/json";
    }
    let response;
    try {
      response = await this.fetcher(url.href, { method, headers,
        body: data === undefined ? undefined : JSON.stringify(data),
        credentials: "same-origin", cache: "no-store", redirect: "error",
        signal: AbortSignal.timeout(20000) });
    } catch {
      throw new InvitationError("Connection interrupted. The result could not be confirmed.");
    }
    if (response.status === 401 || response.status === 403) {
      throw new InvitationError("An active Authentik administrator session is required. Sign in to administration and reload this page.");
    }
    if (!response.ok) throw new InvitationError(`Authentik could not complete the request (HTTP ${response.status}).`);
    if (response.status === 204) return null;
    try { return await response.json(); }
    catch { throw new InvitationError("Unexpected response from Authentik. No further action was taken."); }
  }

  async list(path) {
    let next = path;
    const results = [], visited = new Set();
    while (next) {
      if (visited.has(next) || visited.size >= 100) throw new InvitationError("The user list could not be loaded completely.");
      visited.add(next);
      const page = await this.api(next);
      // Admin authenticator APIs in some versions return a plain list.
      if (Array.isArray(page)) { results.push(...page); break; }
      if (!page || !Array.isArray(page.results) || !page.pagination
        || typeof page.pagination.total_pages !== "number"
        || typeof page.pagination.current !== "number") {
        throw new InvitationError("The Authentik API format has changed. Please contact the administrator.");
      }
      results.push(...page.results);
      if (page.pagination.current < page.pagination.total_pages) {
        const url = new URL(path.startsWith(API_ROOT) ? path : API_ROOT + path, this.origin());
        url.searchParams.set("page", String(page.pagination.current + 1));
        next = url.pathname + url.search;
      } else next = null;
    }
    return results;
  }

  async requireAdmin() {
    const identity = await this.api("core/users/me/");
    if (!identity?.user || identity.user.is_active !== true || identity.user.is_superuser !== true) {
      throw new InvitationError("Only Authentik administrators can use this page.");
    }
    return identity.user;
  }

  passkeyOwners(devices) {
    // The native admin WebAuthn endpoint does NOT filter by a `user` query
    // parameter. Read its complete paginated inventory and match owners here.
    const owners = new Set();
    for (const device of devices) {
      if (!device.user || !/^\d+$/.test(String(device.user.pk))) {
        throw new InvitationError("The passkey inventory could not be matched to users. No invitation was sent.");
      }
      owners.add(String(device.user.pk));
    }
    return owners;
  }

  async load() {
    const admin = await this.requireAdmin();
    const flowSlug = this.test ? "mobile-attendance-qa-enroll" : FLOW_SLUG;
    const groupName = this.test ? "fake" : APPROVAL_GROUP;
    const [users, flows, recoveryFlows, devices] = await Promise.all([
      this.list("core/users/?page_size=100&include_groups=true"),
      this.list(`flows/instances/?slug=${flowSlug}&page_size=100`),
      this.test ? [] : this.list(`flows/instances/?slug=${RECOVERY_FLOW_SLUG}&page_size=100`),
      this.list("authenticators/admin/webauthn/?page_size=100"),
    ]);
    const flow = flows.find((entry) => entry.slug === flowSlug && entry.designation === "enrollment");
    if (!flow?.pk) throw new InvitationError("The controlled first-time enrollment flow is unavailable.");
    const recoveryFlow = recoveryFlows.find((entry) => entry.slug === RECOVERY_FLOW_SLUG
      && entry.designation === "enrollment");
    const owners = this.passkeyOwners(devices);
    const candidates = users.filter((user) => approved(user, groupName) && !duplicateEmail(users, user.email)
      && (!this.test || (!user.is_superuser && !owners.has(String(user.pk))
        && user.path === "qa/mobile-attendance"
        && user.email === `${user.username}@attendance-qa.example.invalid`)));
    const eligible = candidates.map((user) => ({ ...user,
      invitationKind: this.test ? "enrollment" : invitationKind(user, owners.has(String(user.pk))) }));
    eligible.sort((a, b) => (a.name || a.username).localeCompare(b.name || b.username));
    return { users: eligible, flow, recoveryFlow, delivery: this.test ? admin.email : undefined };
  }

  async expire(pk) {
    await this.api(`${INVITATIONS}${encodeURIComponent(pk)}/`, {
      method: "PATCH", data: { expires: new Date(this.now() - 60000).toISOString() },
    });
  }

  async send(userPk, hours, attempts = this.attemptsAvailable ? DEFAULT_ATTEMPTS : 1) {
    if (this.busy) throw new InvitationError("An invitation is already being processed.");
    if (!Number.isInteger(hours) || !EXPIRY_HOURS.includes(hours)) throw new InvitationError("Choose an available expiry.");
    if (!Number.isInteger(attempts) || !ATTEMPTS.includes(attempts)) throw new InvitationError("Choose 1 to 5 attempts.");
    if (attempts > 1 && !this.attemptsAvailable) throw new InvitationError("This site allows one attempt per link. No invitation was sent.");
    if (!/^\d+$/.test(String(userPk))) throw new InvitationError("Choose a user from the list.");
    this.busy = true;
    let created = null, creationAttempted = false, name = null;
    try {
      await this.requireAdmin();
      // Read again immediately before writing: do not trust the page's earlier
      // user list, a typed email, an earlier approval, or a cached device list.
      const { users, flow: enrollmentFlow, recoveryFlow, delivery } = await this.load();
      const user = users.find((entry) => String(entry.pk) === String(userPk));
      if (!user) throw new InvitationError("This user is no longer eligible. They must be active, approved and have a unique email.");
      if (this.test && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(delivery || "")) {
        throw new InvitationError("Set an email address on your administrator account before sending a test invitation.");
      }
      const flow = user.invitationKind === "recovery" ? recoveryFlow : enrollmentFlow;
      if (!flow?.pk) throw new InvitationError("The controlled passkey recovery flow is not yet available. No invitation was sent.");
      const invitations = await this.list(`${INVITATIONS}?flow__slug=${flow.slug}&page_size=100`);
      if (invitations.some((entry) => entry.flow === flow.pk
        && entry.fixed_data?.email?.toLowerCase() === user.email.toLowerCase()
        && Date.parse(entry.expires) > this.now())) {
        throw new InvitationError("This user already has a valid invitation. Open Invitations in Authentik to resend or expire it first.");
      }
      if (!csrfCookie(this.cookie())) throw new InvitationError("Refresh your Authentik administrator session before sending.");
      name = `enroll-${this.test ? user.username : user.pk}-${this.uuid()}`;
      const expires = new Date(this.now() + hours * 3600000).toISOString();
      creationAttempted = true;
      created = await this.api(INVITATIONS, { method: "POST", data: {
        name, expires, flow: flow.pk, single_use: attempts === 1,
        fixed_data: { email: user.email, user_id: user.pk, ...(this.test ? { username: user.username } : {}),
          ...(attempts > 1 ? { attempts } : {}) },
      } });
      if (!created?.pk) throw new InvitationError("Invitation creation could not be confirmed.");
      await this.api(`${INVITATIONS}${encodeURIComponent(created.pk)}/send_email/`, {
        method: "POST", data: { email_addresses: [this.test ? delivery : user.email],
          template: this.test ? "email/cloud-test-passkey-invitation.html" : user.invitationKind === "recovery"
            ? "email/cloud-recovery-invitation.html" : "email/cloud-enrollment-invitation.html" },
      });
      return { email: this.test ? delivery : user.email, expires, kind: user.invitationKind, attempts };
    } catch (error) {
      if (creationAttempted) {
        try {
          // Recover a timed-out creation by its unique generated name. Never
          // retry creation or mail submission automatically.
          const matches = created?.pk ? [created]
            : await this.list(`${INVITATIONS}?name=${encodeURIComponent(name)}&page_size=100`);
          for (const invitation of matches) {
            if (invitation.name !== name || !invitation.pk) throw new Error("Unexpected invitation");
            await this.expire(invitation.pk);
          }
          throw new InvitationError("Sending could not be confirmed. Any invitation found for this attempt was expired. An email might still arrive with an expired link; you can try again.");
        } catch (cleanupError) {
          if (cleanupError instanceof InvitationError && cleanupError.message.startsWith("Sending could not")) throw cleanupError;
          throw new InvitationError("Sending could not be confirmed and automatic expiry could not be verified. Check Invitations in Authentik before retrying.");
        }
      }
      throw error;
    } finally { this.busy = false; }
  }
}
