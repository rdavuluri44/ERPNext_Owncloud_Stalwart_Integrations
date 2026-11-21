# Test site: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 21 November 2026
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
Branch `p63-demo-ui` (UI points) is on test awaiting the owner's browser check before its PR.
**Domain split (owner, 21 November 2026; P70):** the demo gets its own identity: `example.com` mail and a second
WhatsApp number; production moves to `tenant.example`. Effect on P63: (a) demo mail and messages are sent **as
Unformat**, no longer through a production sending account (`test_form_smtp` is replaced by the demo's own account),
which also removes the tenant from what the demo sends; (b) scope 5 (only the test group receives) **stays and matters
more**: the refreshed data still holds real vendors' addresses and numbers, so without the allow list a demo user could
message a real vendor as Unformat; employees enrol through an authentik group, vendors as decided above; (c) scope 6
(test/demo marker) applies to all `example.com` mail and Unformat WhatsApp messages; (d) new questions moved to P70:
where `example.com` mail runs, the second WhatsApp number (P04). P63, P70 and P19 are taken up together.


### P66 — Errors on the test site are invisible: Error Log rows stay queued

**App:** test-site · **Also touches:** general, erp · **State:** open

**Status:** open (found 21 November 2026). Frappe writes Error Log rows by a deferred insert that the scheduler
flushes; the business scheduler is deliberately off on the test copy, so every error stays in the Redis cache queue
(`insert_queue_for_Error Log`, 39 records on 21 November) and the Error Log list looks empty. Diagnosis needed reading
the queue by hand. **Fix:** flush the deferred inserts on test on a short timer (only that job, not the business
scheduler), or a small read tool; plus an alarm on new error records (with P61's alarms). Check whether production
flushes them (its scheduler runs).
