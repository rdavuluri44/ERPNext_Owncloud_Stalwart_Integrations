# Test site: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 28 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Test site: P items

The permanent test site: refresh, branch deploys and the demo.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P51 — Data refresh runs at 8 pm, not on demand

**App:** test-site · **Also touches:** none · **State:** open

**Status:** open, owner request 19 November 2026; work on it later, after the
crippled refresh (PR #3 of the public repository) is merged and in use.
Scrambling the production copy is resource intensive, so pressing "Refresh
data" must not start it at once. Instead the request is queued and starts at
**8 pm** (Asia/Kolkata), and the refresh page shows a line saying so, for
example "Data refresh scheduled for 8 pm today". Owner clarification, same
day: the allowed window is **8 pm to 8 am the next morning**. A request made
before 8 pm is scheduled for 8 pm; a request made inside the window may run
at once. My assumptions to confirm when we build it: only "Refresh data" is
scheduled ("Refresh code" stays immediate); a request made between 8 am and
8 pm waits for 8 pm; a run starts only if it is expected to **finish
by 8 am** (owner, same day): the expected duration comes from the previous
successful data refreshes plus a safety margin (a generous default until one
has run), so a request made late at night, too late to finish, waits for the
next 8 pm instead of running into working hours; repeated
presses merge into one queued run; the page shows who requested it, when it
will run, and its progress; a queued request can be cancelled before it
starts. **Code refresh (owner question, same day):** its duration is not
measured (the ERP image rebuild is the slow part; the container swap took
about two minutes on production). Build the scheduling rule once as a setting
per button: on for "Refresh data", off at first for "Refresh code"; measure
real code refreshes and switch it on if they prove heavy (for example over 15
minutes), with the 8 am finish estimate taken from that button's own history.
Never apply it to the colleague's own branch deploys, which must stay
immediate. Where: `test-refresh` module (worker and refresh page).

### P54 — Branch deploy button for the "developer" group on the test site

**App:** test-site · **Also touches:** none · **State:** blocked

**Status:** open, owner decision 20 November 2026. **Blocked until the first crippled refresh passes its audit** (exporter deployed on production 20 November, residual items listed in the release log). The authentik group
"developer" exists (flat, no bindings, one member: the colleague) and is meant
to be allowed to deploy branches to the test site without asking the owner.
The deploy mechanism does not exist yet (PR #3 only adds "Refresh code", which
resets test to `main`). To build in `test-refresh`: a test-site page where a
member of "developer" picks a branch of the public repository or a pull
request, the repository checks run, and the branch is built and deployed to
test, showing who deployed which revision and when; "Refresh code" puts `main`
back. Safeguards to include: only members of the group may use it (checked on
the server, not just hidden in the page); test runs crippled data only (PR #3)
and its outbound-integration guard stays; deploy only from the public
repository; no production credentials on the test host; every deploy logged.
Accepted risk (owner): deploying runs the branch's code on the test VM.
Needs: PR #3 merged and the first crippled refresh done first.

### P63 — Demo mode for the test site (`test.example.com`): neutral brand, no tenant traces

**App:** test-site · **Also touches:** portal, signin, mail, erp · **State:** in progress

**Status:** open, owner request 21 November 2026; not started. No earlier P item covered
this; related: P47 (landing page), P55 (brand mechanism), P51 and P54 (crippled refresh),
P35 (public sharing). The owner wants `test.example.com` usable as a **demo**. Its data is
already crippled (names and identities of non-kept users removed, 60 days only); now every
trace of the tenant goes too.

**Intent (owner restatement, 21 November 2026):** (i) totally clean demo data on the test site, with no trace of
the tenant after every refresh; (ii) authentik shows its own UN/format brand when signing in to the demo; (iii) test
mail and messages reach only the people enrolled for testing (scope 5), each marked as test/demo (scope 6).
**Go:** owner, 21 November 2026 (whole scope).

**Scope**
1. **Remove the tenant everywhere on the test site:** the name <tenant> and the company logo
   from the landing page, portal (eZone), sign-in pages, favicons (ERP, portal, authentik, webmail,
   Drive, push icons), page titles, browser tab and link-preview text, ERP records that carry
   the company name (Company, addresses, letterheads, print and email templates, system and
   website settings), Drive spaces and DMS items where the name appears. The refresh must
   re-apply this after every data refresh (extend the crippling step), and a check must fail
   if the tenant name appears anywhere in the refreshed copy.
2. **Dummy logo:** big letters **UN** in the first row and **format** in small letters in the
   second row, scaled to exactly the width of the first row (as with "EMPLOYEE ZONE" on the
   landing page). **Propose several colour combinations** as mock-ups for the owner to choose
   from (for example dark blue with orange, graphite with teal, deep green with amber, plum
   with coral, black with a single accent). Used for every favicon and the whole site, replacing
   the <tenant> logo; a compact favicon variant for 16 to 48 px.
3. **Demo landing page with line art:** drawn in the style of the owner's sample (black outline
   drawing with a few flat colour accents on a light grey background; sample kept in the
   private assets as `assets/demo-landing/sample-flower-bee-owner-sketch.webp`: a flower with
   orange centre, green stem and leaves, and a small bee). Our own vector artwork, redrawn
   (rights: owner's own sketch and our own drawing), and drawn stroke by stroke like the
   production landing page. (Owner, 21 November 2026: the entry reads "Apps" as a badge top left and the typed
   line is dropped on the demo; see the progress notes.)
4. **Mechanism:** tenant branding already lives in the private runtime profile (`company_logo`,
   `company_favicon_dir`, website title and name, landing assets, P55), so the demo brand is
   a second set of private assets selected by the test profile; production keeps its own. The
   public repository stays tenant-neutral; the UN/format logo and demo art may be published
   as the neutral default.

5. **Outbound mail and messages only to the test group (owner, 21 November 2026; replaces "mute"):** muting
   e-mail and messages on the test site is not acceptable, because flows such as invitations, approvals, purchase
   orders and WhatsApp replies must be tested end to end. Instead every outbound channel (ERP mail, Mail/Stalwart
   relay, WhatsApp and other messaging, push) delivers **only to recipients enrolled in the test group** and drops or
   holds everything else (with a log line, never a silent loss). **Employees** are enrolled through authentik (a
   test group, for example the existing Testers group). **Vendors get no login**, so they need a separate enrolment:
   to decide how (for example a "test recipients" list of vendor mail addresses and phone numbers kept in the private
   test profile, or a flag on the Supplier record that a refresh keeps), who may add them, and their consent. The
   refresh must keep the allow list (production data never widens it) and a check must prove that a message to a
   non-enrolled address is not sent. This changes the documented outbound safeguard: record it in
   `docs/decisions.md` and the test-refresh module README when adopted.
6. **Every outgoing message is marked as test/demo (owner, 21 November 2026):** this is an exclusive test setup,
   so everything it sends carries a visible marker. **E-mail:** a banner at the top of the body ("This is a TEST /
   DEMO message sent from the evaluation system. It is not a real business communication.") in both the HTML and the
   plain-text part, a `[TEST]` (or `[DEMO]`) prefix on the subject, and a header (for example `X-Test-Message: yes`).
   **WhatsApp, SMS and push:** a `[TEST]` prefix on the text. Applied at the last step before a message leaves (the
   mail relay and each messaging adapter), so no sender, template or app can skip it; production never adds it.
   A check sends one message per channel to an enrolled recipient and verifies the marker.

**Open questions for planning:** (a) test and production **share one authentik**, and its brand
is chosen by the request's host name (`sso`), so the sign-in page cannot show the demo logo for test
only without a separate sign-in host name for the demo (or accepting the shared page); (b) who may
see the demo (the Testers group, or public with sample accounts) and whether the TEST SITE
marker stays; (c) demo user accounts and passwords stay out of Git; (d) outbound
mail and integrations: answered by scope 5 (allow list of the test group instead of quarantine); open: how vendors are enrolled.

**Progress (21 November 2026): demo logo live on the test site.** Owner chose option **A, navy and orange**
(`#1F3A5F` UN, `#E8731A` format) from five combinations (A navy/orange, B graphite/teal, C green/amber, D
plum/coral, E black/blue; mock-ups and files in the private assets `assets/unformat-demo-brand/`). Logo: "UN" in
heavy type, "format" below stretched to exactly the width of "UN" (SVG `textLength`, so it holds in any font);
favicon: rounded navy tile, white "UN", orange bar. Installed through the test profile (`company_logo`,
`company_favicon_dir`, `website_title`/`website_name` = Unformat; rollback copy of the profile in
`<server path>`). Verified byte for byte: ERP logo and favicons, landing page logo and
favicon; the landing page title is "Unformat" and no longer contains the tenant name. **Still showing the tenant:** the
portal heading (the ERP Company record "<tenant company>", business data in the test copy: rename
or mask it in the refresh's crippling step, not by hand), the sign-in page (shared authentik brand, see open question a),
and anything inside the data (letterheads, print formats, mail). **Not yet:** the line-art landing page, re-applying
all of this after every data refresh, publishing the neutral brand as the repository default. Lesson for P67: the test
deploy skips the ERP image build when an image of the same commit exists, so a brand-only change needed the image tag
removed first; browsers may also keep the old files because the version stamp is the commit.

**Progress (21 November 2026, branch `p63-demo-ui`, on test at `00669d0`, not merged):** owner's eight UI points. Landing
page: new flower-and-bee drawing after the owner's sketch (outlines drawn, then coloured; bee hovers), no tagline, the
entry reads "Apps" as a navy (`#1F3A5F`, the colour of "UN") badge top left mirroring the TEST SITE badge. Gateway: `/`
shows the landing page only without an ERP session, so after sign-in the portal sits at `test.example.com/` with a clean
address (the portal also rewrites `/place_holder` to `/`); this replaces P60. Portal (same page on test and production):
logo without the company name; refresh buttons in one row beside the logo, dates under them, status line only while a
refresh runs. One-click entry: expected to work now that the gateway returns to the requested page (P65); owner to
confirm. **Remaining:** owner browser check, then PR and merge; company-name masking in refreshed data, sign-in brand.

**Paused (owner, 21 November 2026): resume here when P63 is taken up again.** Scope 5 and 6 are not started. Decisions
waiting for the owner (recommendation first):
1. **Vendor enrolment** (vendors have no login): (a, recommended) a short list of vendor mail addresses and phone
   numbers in the test site's private profile, added on the owner's word; survives every refresh and never comes from
   production; or (b) a "test recipient" tick on the Supplier record in the test ERP, set by staff, which the refresh
   must preserve.
2. **How the test ERP sends mail:** today `mute_emails` and the disabled scheduler keep it silent, and the test egress
   firewall allows only the SSO host and the test form SMTP address. (a, recommended) turn mail on but keep every other
   scheduled job off; a small **test mail gateway** on the test site flushes the ERP mail queue every minute and is the
   only way out: it delivers only to the test group (authentik group for employees, plus the vendor list), adds the
   banner, the `[TEST]` subject prefix and the `X-Test-Message` header, and holds and logs everything else; or (b) run
   the test ERP's scheduler fully, behind the same gateway (more realistic, more goes out).
**Design notes:** the gateway sends through the existing dedicated test sending account (`test_form_smtp`), so the
egress rule stays one address; the test Mail server's own outgoing mail must also go through the gateway; WhatsApp is
not live yet (P04), so its adapter gets the same allow list and `[TEST]` prefix when built; push stays off on test.
Branch `p63-demo-ui` (UI points): see the progress note of 21 November evening below.
**Domain split (owner, 21 November 2026; P70):** the demo gets its own identity: `example.com` mail and a second
WhatsApp number; production moves to `tenant.example`. Effect on P63: (a) demo mail and messages are sent **as
Unformat**, no longer through a production sending account (`test_form_smtp` is replaced by the demo's own account),
which also removes the tenant from what the demo sends; (b) scope 5 (only the test group receives) **stays and matters
more**: the refreshed data still holds real vendors' addresses and numbers, so without the allow list a demo user could
message a real vendor as Unformat; employees enrol through an authentik group, vendors as decided above; (c) scope 6
(test/demo marker) applies to all `example.com` mail and Unformat WhatsApp messages; (d) new questions moved to P70:
where `example.com` mail runs, the second WhatsApp number (P04). P63, P70 and P19 are taken up together.

**Progress (21 November 2026, evening): UI accepted by the owner, PR #20 open (tested at `a0cb527`).** Second round of owner
feedback done on test: Apps badge exactly the TEST SITE badge's size; flower and bee at 60%, beside the logo (logo and
flower centred together; below the logo on phones); demo logo redrawn ("format" inside the width of "UN", its letters of
slightly different size and height, tight margins; private assets `assets/unformat-demo-brand/logo.svg`, previous kept in
`options/`; on test from `<test host secrets folder>/brand-unformat-demo-2026-11-21b`); portal logo 50 px, 8 px lower and
12 px to the right, refresh row moved right. **Owner rule: production and test have separate asset sets.** The portal's
site-specific look now comes from site settings (`cloud_portal_hide_entity_name`, `cloud_portal_logo_height`,
`cloud_portal_logo_position`, `cloud_portal_clean_root_address`), set on test through `erp_site_settings` in the private
profile; production sets none and keeps its page exactly (guard test; production landing page pixel-identical to
`main`). Owner: "its perfect". **Owner decision on (i)/(ii):** keep as it is: signed in, `/` opens the apps; signed out,
the landing page. Rollback copies on test: `<server path>`. **Remaining for P63:** clean
refreshed data (company name masking), sign-in brand, scope 5 and 6 (paused, decisions waiting above), with P70 and P19.

**Final demo logo (owner, 21 November 2026, "This is final"):** "UN" in navy over "tamrof" in orange (`format` written
right to left, letters upright; the last `f` mirrored left to right; letters of slightly different size and height,
inside the width of "UN"). The flower twig stays separate from the logo, standing beside it as before; colours
unchanged. Tried and not chosen: a half-turned `t`, a mirrored `a`, the twig lying flat under the word, the flower
inside the logo, six multicolour sets (kept in `assets/unformat-demo-brand/options/colour-sets-2026-11-21/`). Installed
on test from `<test host secrets folder>/brand-unformat-demo-2026-11-21c` (ERP image rebuilt for the same commit
`a0cb527`); landing page and app page checked. Private asset only: no code change, PR #20 unchanged.

**Released (21 November 2026, 16:38 UTC):** PR #20 merged (`6db2536`) and promoted; production looks exactly as before
(no look settings; www pixel-identical). The test site keeps its demo look through its own settings and assets.


### P66 — Errors on the test site are invisible: Error Log rows stay queued

**App:** test-site · **Also touches:** general, erp · **State:** open

**Status:** open (found 21 November 2026). Frappe writes Error Log rows by a deferred insert that the scheduler
flushes; the business scheduler is deliberately off on the test copy, so every error stays in the Redis cache queue
(`insert_queue_for_Error Log`, 39 records on 21 November) and the Error Log list looks empty. Diagnosis needed reading
the queue by hand. **Fix:** flush the deferred inserts on test on a short timer (only that job, not the business
scheduler), or a small read tool; plus an alarm on new error records (with P61's alarms). Check whether production
flushes them (its scheduler runs).

### P101 — Test Drive, test Paperless, test mail and the test editor sign in through the test sign-in server

**App:** test-site · **Also touches:** signin, drive, dms, mail, editor · **State:** open

**Why (found 27 November 2026, during the P98 browser check; owner chose this fix):** on 23 November only the test
ERP moved to the separate test sign-in server (`test-sso.example.com`). Test Drive (production client `test-office`)
and test mail (`test-office-mail`), and with Drive the test editor, still sign in through the production sign-in
server. Their production entries admit only `Testers`; the owner's account left that group on 24 November (owner:
use the native test administrator on the test server), so production now refuses the owner for test Drive
("Permission denied", policy binding result False). Inside the ERP portal the Drive panel then stays empty, because
the sign-in page refuses to be shown in a frame. **Test Paperless too** (owner, 27 November 2026: "paperless and
owncloud doesn't work from test.example.com"): checked read-only, its only sign-in is OpenID through
`sso.example.com` (regular login switched off, redirect to the sign-in server on), so the same refusal applies. It also means testing still depends on production sign-in, against
the owner's decision that testing uses no production data.

**What (proposal, owner to confirm before work):**
1. Read-only inventory: every test app's issuer and client (Drive web, desktop and mobile clients; Paperless; webmail; the
   editor through Drive; anything else on test still pointing at production), and what each production test entry is bound
   to.
2. Create the matching clients on the test sign-in server from the repository (blueprints or tools, not by hand),
   with the same rules as the ERP: who may sign in, passkey flow.
3. Point test Drive, test Paperless, test webmail and the test editor at the test server through the test profiles;
   deploy on test; check sign-in, the portal's Drive and Paperless panels, opening an office document, webmail.
4. Then retire the production entries for those test apps (`test-office`, `test-office-mail` and any others found)
   with the existing fail-closed retirement procedure (23 November, `0c8544d`), on the owner's go.

**Not decided:** whether test Drive's existing users and shares (linked to production identities) must be mapped
to the test server's users, or the test Drive data is reset with the next test refresh; whether the Drive desktop and
phone clients are covered now or later; order with P63 (demo mode) and P70 (domain split).

**Acceptance:** the owner signs in to test Drive, test Paperless, test webmail and a test office document with the test
administrator account through `test-sso`, and the portal's Drive and Paperless panels load; no test app trusts the production
sign-in server; the production test entries are retired.

**Related:** P76 and P77 (test sign-in server), P63, P70, P25, P69 (test webmail reader), P98 (where it was found).

### P105 — Test site ready for the native app's five-phone test round

**App:** test-site · **Also touches:** erp, signin, mobile · **State:** blocked

**Why (owner, 27 November 2026: "go for rest of all" on the native app developer's request, public PR #114,
issuecomment-7214300268):** the first test round of the native Android app (P50, Phase 1) runs on five phones in the
office, one role per phone, against the test site only.

**What (from the request, Part A):**
1. Five test people, one per role, invited in the test sign-in service and in the group that allows ERPNext, each
   with an ERPNext user with exactly the roles a real person in that job has (site supervisor `Field Supervisor`,
   engineer `Field Attendance Verifier`, project manager `Field Attendance Approver`, HR `HR User`, admin
   `Field Attendance Manager`), a linked Employee, user permissions limited to their project or site, and reporting
   lines (supervisor and engineer report to the project manager).
2. A sixth account, invited but with no ERPNext role, that can be disabled on request.
3. Made-up test data: one project with one site fenced at the office, a second project none of the five belongs to,
   about ten workers under the supervisor, two attendance entries waiting for the project manager, one returned to
   the supervisor, one request in a workflow. Start from `tools/seed_mobile_attendance_qa.py`.
4. An ERPNext OAuth client for the native app (public, PKCE S256, no secret, scopes `all openid`), redirect an https
   App Link on the test domain (agent's recommendation over a private scheme), the client ID in
   `cloud_native_mobile_clients`, and `assetlinks.json` with the test build's SHA-256 fingerprint.

**Blocked on:** the testers' mail addresses (to the owner privately, never in the public PR); the colleague collects
them (owner, 27 November). The signing fingerprint arrived on #114 on 27 November (issuecomment-7216179275).

**Acceptance:** each of the five signs in on their own phone with their own passkey and sees only their role's
screens; every "must be refused" call in the request is refused by ERPNext itself; the sixth account gets the clear
"signed in but not allowed" message.

**Related:** P50, P82, P95, P103, P104.
