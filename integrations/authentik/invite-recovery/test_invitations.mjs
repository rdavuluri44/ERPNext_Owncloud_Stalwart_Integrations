import assert from "node:assert/strict";
import { InvitationClient, FLOW_SLUG, RECOVERY_FLOW_SLUG, approved, invitationKind } from "./public/invitations.mjs";

const baseUser = { pk: 7, name: "Test user", username: "test-user", email: "test@example.invalid",
  type: "internal", is_active: true, groups_obj: [{ name: "Workspace Users" }], attributes: {}, last_login: null };
const flow = { pk: "enrollment-id", slug: FLOW_SLUG, designation: "enrollment" };
const recoveryFlow = { pk: "recovery-id", slug: RECOVERY_FLOW_SLUG, designation: "enrollment" };
const testFlow = { pk: "test-enrollment-id", slug: "mobile-attendance-qa-enroll", designation: "enrollment" };
const synthetic = { ...baseUser, username: "fake-engineer", email: "fake-engineer@attendance-qa.example.invalid",
  path: "qa/mobile-attendance", groups_obj: [{ name: "fake" }] };
const adminEmail = "operator@example.invalid";
const now = Date.parse("2026-11-06T08:00:00Z");
function fixture({ user = baseUser, devices = [], admin = true, csrf = true,
  sendFails = false, cleanupFails = false, duplicate = false, activeInvite = false,
  missingRecovery = false, listFails = false, test = false, delivery = adminEmail,
  attemptsAvailable = false, activeSingleUse = true } = {}) {
  const requests = [], invitations = [];
  const client = new InvitationClient({
    test, attemptsAvailable,
    origin: () => "https://sso.example.invalid", now: () => now,
    cookie: () => csrf ? "authentik_csrf=test-csrf" : "", uuid: () => "test-attempt",
    fetcher: async (url, request) => {
      const path = new URL(url).pathname.replace("/api/v3/", "");
      const query = new URL(url).searchParams;
      requests.push({ path, ...request, data: request.body ? JSON.parse(request.body) : undefined });
      const reply = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
      const page = (results) => reply({ results, pagination: { current: 1, total_pages: 1 } });
      if (path === "core/users/me/") return reply({ user: { is_active: true, is_superuser: admin, email: delivery } });
      if (path === "core/users/") return page(duplicate ? [user, { ...user, pk: 8 }] : [user]);
      if (path === "flows/instances/") {
        if (query.get("slug") === testFlow.slug) return page([testFlow]);
        return page(query.get("slug") === FLOW_SLUG ? [flow] : missingRecovery ? [] : [recoveryFlow]);
      }
      if (path === "authenticators/admin/webauthn/") return listFails ? reply({}, 500)
        : page(devices.map((d) => ({ user: { pk: user.pk }, ...d })));
      if (path === "stages/invitation/invitations/" && request.method === "GET") {
        return page(activeInvite ? [{ flow: devices.length ? recoveryFlow.pk : flow.pk, single_use: activeSingleUse,
          expires: new Date(now + 3600000).toISOString(), fixed_data: { email: user.email } }] : invitations);
      }
      if (path === "stages/invitation/invitations/" && request.method === "POST") {
        const invitation = { ...JSON.parse(request.body), pk: "new-invitation" };
        invitations.push(invitation);
        return reply(invitation, 201);
      }
      if (path.endsWith("/send_email/")) return sendFails ? reply({}, 500) : reply(null, 204);
      if (path.endsWith("/new-invitation/") && request.method === "PATCH") return cleanupFails ? reply({}, 500) : reply({}, 200);
      throw new Error(`Unhandled fixture request ${path}`);
    },
  });
  return { client, requests, invitations };
}

export async function runTests() {
  let passed = 0;
  async function check(name, fn) { await fn(); passed++; }
  const writes = (f) => f.requests.filter((r) => r.method !== "GET");
  await check("approval excludes inactive, unapproved and service accounts", () => {
    assert(approved(baseUser));
    for (const patch of [{ is_active: false }, { groups_obj: [] }, { type: "service_account" }, { email: "" }])
      assert.equal(approved({ ...baseUser, ...patch }), false);
  });
  await check("registered users and established accounts use recovery", () => {
    assert.equal(invitationKind(baseUser, false), "enrollment");
    assert.equal(invitationKind(baseUser, true), "recovery");
    assert.equal(invitationKind({ ...baseUser, last_login: "2026-10-01" }, false), "recovery");
    assert.equal(invitationKind({ ...baseUser, attributes: { cloud_verified_email: baseUser.email } }, false), "recovery");
  });
  await check("non-admin cannot enumerate users or write", async () => {
    const f = fixture({ admin: false });
    await assert.rejects(f.client.load(), /Only Authentik administrators/);
    assert.equal(f.requests.length, 1); assert.equal(writes(f).length, 0);
  });
  await check("duplicate active email addresses cannot be invited", async () => {
    const f = fixture({ duplicate: true });
    assert.equal((await f.client.load()).users.length, 0);
    await assert.rejects(f.client.send(7, 24), /no longer eligible/);
    assert.equal(writes(f).length, 0);
  });
  await check("device lookup failure stops all writes", async () => {
    const f = fixture({ listFails: true });
    await assert.rejects(f.client.send(7, 24)); assert.equal(writes(f).length, 0);
  });
  await check("ineligible user is checked again before sending", async () => {
    const f = fixture({ user: { ...baseUser, groups_obj: [] } });
    await assert.rejects(f.client.send(7, 24), /no longer eligible/); assert.equal(writes(f).length, 0);
  });
  await check("arbitrary expiries and free text users cannot be submitted", async () => {
    const f = fixture();
    await assert.rejects(f.client.send(7, 10000), /expiry/);
    await assert.rejects(f.client.send("someone@example.invalid", 24), /Choose a user/);
    assert.equal(f.requests.length, 0);
  });
  await check("missing CSRF prevents every write", async () => {
    const f = fixture({ csrf: false });
    await assert.rejects(f.client.send(7, 24), /session/); assert.equal(writes(f).length, 0);
  });
  await check("first-time invitation fills data and mails exact approved recipient", async () => {
    const f = fixture(); const result = await f.client.send(7, 24);
    assert.equal(result.kind, "enrollment");
    assert.deepEqual(f.invitations[0].fixed_data, { email: baseUser.email, user_id: 7 });
    assert.equal(f.invitations[0].flow, flow.pk); assert.equal(f.invitations[0].single_use, true);
    assert.equal(Date.parse(f.invitations[0].expires), now + 24 * 3600000);
    const sent = f.requests.find((r) => r.path.endsWith("/send_email/"));
    assert.deepEqual(sent.data.email_addresses, [baseUser.email]);
    assert.equal(sent.data.template, "email/cloud-enrollment-invitation.html");
    assert.equal(sent.headers["X-authentik-CSRF"], "test-csrf");
  });
  await check("existing keys route to separate recovery flow without deletion at send", async () => {
    const f = fixture({ devices: [{ pk: 4 }] }); const result = await f.client.send(7, 6);
    assert.equal(result.kind, "recovery"); assert.equal(f.invitations[0].flow, recoveryFlow.pk);
    assert.equal(f.requests.find((r) => r.path.endsWith("/send_email/")).data.template, "email/cloud-recovery-invitation.html");
    assert.equal(writes(f).length, 2);
    assert(!f.requests.some((r) => r.method === "DELETE"));
  });
  await check("unconfigured recovery does not fall back to first-time enrollment", async () => {
    const f = fixture({ devices: [{ pk: 4 }], missingRecovery: true });
    await assert.rejects(f.client.send(7, 24), /recovery flow is not yet/); assert.equal(writes(f).length, 0);
  });
  await check("another user's key cannot turn first-time enrollment into recovery", async () => {
    const f = fixture({ devices: [{ pk: 4, user: { pk: 99 } }] });
    const result = await f.client.send(7, 24);
    assert.equal(result.kind, "enrollment");
  });
  await check("unreadable device ownership fails closed", async () => {
    const f = fixture({ devices: [{ pk: 4, user: null }] });
    await assert.rejects(f.client.send(7, 24), /inventory could not be matched/);
    assert.equal(writes(f).length, 0);
  });
  await check("existing live invitation blocks accidental duplicate email", async () => {
    const f = fixture({ activeInvite: true });
    await assert.rejects(f.client.send(7, 24), /already has a valid invitation/); assert.equal(writes(f).length, 0);
  });
  await check("mail submission failure expires the new invitation", async () => {
    const f = fixture({ sendFails: true });
    await assert.rejects(f.client.send(7, 24), /was expired/);
    const patch = f.requests.find((r) => r.method === "PATCH");
    assert(Date.parse(patch.data.expires) < now);
  });
  await check("failed cleanup cannot claim the invitation was expired", async () => {
    const f = fixture({ sendFails: true, cleanupFails: true });
    await assert.rejects(f.client.send(7, 24), /automatic expiry could not be verified/);
  });
  await check("API calls cannot send session data to another origin", async () => {
    const f = fixture();
    await assert.rejects(f.client.api("/api/v3/../../elsewhere"), /Unexpected API/);
    assert.equal(f.requests.length, 0);
  });
  await check("test invitation fixes the synthetic identity and delivers to the signed-in administrator", async () => {
    const f = fixture({ test: true, user: synthetic });
    assert.equal((await f.client.load()).users.length, 1);
    assert.equal((await f.client.send(7, 24)).email, adminEmail);
    assert.equal(f.invitations[0].flow, testFlow.pk);
    assert.match(f.invitations[0].name, /^enroll-fake-engineer-/);
    assert.deepEqual(f.invitations[0].fixed_data, { email: synthetic.email, user_id: 7, username: synthetic.username });
    const sent = f.requests.find((request) => request.path.endsWith("/send_email/"));
    assert.deepEqual(sent.data, { email_addresses: [adminEmail], template: "email/cloud-test-passkey-invitation.html" });
  });
  await check("test invites exclude existing keys, administrators and real staff identities", async () => {
    const scenarios = [
      { user: synthetic, devices: [{ pk: 4 }] },
      { user: { ...synthetic, is_superuser: true } },
      { user: { ...synthetic, email: "staff@example.invalid" } },
      { user: { ...synthetic, path: "users" } },
      { user: baseUser },
    ];
    for (const scenario of scenarios) {
      const f = fixture({ test: true, ...scenario });
      assert.deepEqual((await f.client.load()).users, []);
      await assert.rejects(f.client.send(7, 24), /no longer eligible/);
      assert.equal(writes(f).length, 0);
    }
  });
  await check("test invitation without a delivery address creates no link", async () => {
    const f = fixture({ test: true, user: synthetic, delivery: "" });
    await assert.rejects(f.client.send(7, 24), /administrator account/);
    assert.equal(writes(f).length, 0);
  });
  await check("P78: sites without attempt support keep single-use links", async () => {
    const f = fixture(); const result = await f.client.send(7, 24);
    assert.equal(f.invitations[0].single_use, true); assert.equal("attempts" in f.invitations[0].fixed_data, false);
    assert.equal(result.attempts, 1);
    const g = fixture();
    await assert.rejects(g.client.send(7, 24, 3), /one attempt per link/); assert.equal(writes(g).length, 0);
  });
  await check("P78: five attempts by default when the site supports them", async () => {
    const f = fixture({ attemptsAvailable: true }); const result = await f.client.send(7, 24);
    assert.equal(f.invitations[0].single_use, false);
    assert.deepEqual(f.invitations[0].fixed_data, { email: baseUser.email, user_id: 7, attempts: 5 });
    assert.equal(result.attempts, 5);
  });
  await check("P78: one attempt stays a native single-use link", async () => {
    const f = fixture({ attemptsAvailable: true }); await f.client.send(7, 24, 1);
    assert.equal(f.invitations[0].single_use, true); assert.equal("attempts" in f.invitations[0].fixed_data, false);
  });
  await check("P78: only 1 to 5 attempts are accepted", async () => {
    for (const attempts of [0, 6, 2.5, "3"]) {
      const f = fixture({ attemptsAvailable: true });
      await assert.rejects(f.client.send(7, 24, attempts), /1 to 5 attempts/); assert.equal(writes(f).length, 0);
    }
  });
  await check("P78: an unexpired reusable link blocks a second invitation", async () => {
    const f = fixture({ attemptsAvailable: true, activeInvite: true, activeSingleUse: false });
    await assert.rejects(f.client.send(7, 24), /already has a valid invitation/); assert.equal(writes(f).length, 0);
  });
  return { passed };
}

await runTests();
