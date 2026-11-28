# Portal (eZone): P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 28 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Portal (eZone): P items

The portal page (eZone, formerly place_holder), its app menu, navigation, and the company landing website.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P07 — Remaining Frappe UI coverage review

**App:** portal · **Also touches:** erp, raven · **State:** open

**Status:** final shared menu is deployed in native Desk apps; Raven/Insights retain their separate native SPA navigation.

Reconcile the user's “all Frappe apps” request against these separate interfaces. Any equivalent shared-action/module layout for those SPAs needs a per-app mapping; it has not been implemented. Do not treat Desk-hook coverage as proof of identical navigation across every installed Frappe-based app.

### P09 — Portal fullscreen toggle

**App:** portal · **Also touches:** none · **State:** open

**Status:** home-logo toggle is implemented; manual browser acceptance is unconfirmed.

A previous automated click reported fullscreen unavailable. Verify a real user click enters and exits fullscreen in the target desktop browser, then check touch/mobile behavior or provide an appropriate fallback if unsupported.

### P47 — Company website as the front door of the app portal

**App:** portal · **Also touches:** none · **State:** in progress

**Status:** planned; scope widened by the owner on 19 November 2026 (first
version was "a minimal website on the VPS and test"). Desktop and laptop
only; mobile devices are handled separately (P50, and its own portal rules).

**Scope (owner):**
- `www.example.com` is the place everyone opens first. It is **always
  reachable, whether signed in or not**.
- Signed out: the public page, with an **Employee Zone** button. Clicking it
  completes single sign-on and shows the portal's auto-hiding app menu.
- Signing out of any app brings the Employee Zone button back.
- Apps open inside the same site like today's portal: ERPNext at
  `www.example.com/#erp`, then Drive, Mail, DMS and the rest, each on its own
  hash route.
- **First version:** very basic: the company logo, a decent background image
  and a banner saying "Launching soon".
- Same site on the test host first (with the TEST marker), then production
  (code → repository → test → production). Content and code as a module in the
  public repository; the real logo and background image are deployment
  assets kept outside the public repository (as the company logo already is).

**Technical notes (mine, to settle when we build it):**
- The portal shell moves from the ERP host to `www`. Every app's allowed
  frame ancestors and parent origin (Drive, Mail, DMS, the editor, ERP) must
  then name `www.example.com`; the Mail move showed what happens when one is
  missed, so each app is checked in the browser, not just by headers.
- The public page is static (own small pinned web container and route file,
  HTTPS through the existing proxy, no access to business data); the portal
  shell loads only after sign-in.
- **Landing page design (owner, 20 November 2026):** the tunnel photo with a
  faded grey overlay as the background; logo, "Launching soon" banner and the
  Employee Zone button on it. Photos from Unsplash (free licence, not open
  source: kept out of the public repository; credit the photographers in the
  footer: grey texture by Mariola Grobelska, tunnel by Ricardo Gomez Angel).
  Apps connect to the **Desk** (the portal after sign-in, P53), not to the
  landing page.
- **Logo (owner):** keep the current logo (the one on authentik) and frame it
  with two L-shaped corner brackets, each its own colour, with gaps between
  them; one bracket orange, the second colour suggested by me. Style modern and
  minimal, black/white plus accents. Mock-ups made 20 November (orange with
  the logo's blue, with teal, with graphite); my recommendation is orange with
  the logo blue (graphite disappears on dark backgrounds). The current logo
  is a raster picture inside an SVG, so a crisp vector redraw is a separate
  option for later. **Owner decision, 20 November 2026 (final after six changes the same
  day): two complete rounded squares behind the white logo panel, in the
  style of the owner's reference icon: blue up-left and orange down-right,
  each a soft vertical gradient (blue `#4FA0E3` to `#0E4A8C`, orange
  `#EE9234` to `#C45E06`), sticking out about 32 px (8 percent of the logo
  width) on two sides, touching the panel with no gap, logo on top. Mock-up
  `mock_G_blue_orange_thinner` (not in Git). The blue echoes the lettering of
  the logo. Earlier variants (orange/teal, purple/orange, graphite) dropped.** **Name:** the landing page shows **<tenant>**. "Unformat" is the
  repository (the product); <tenant> is the tenant using it. So the tenant's
  name, logo and images are deployment settings kept outside the public
  repository, and the public code stays tenant-neutral.
- **Landing page final design (owner, 20 November 2026, after four rounds the
  same day):** white page with an **original pencil drawing** of a tunnel
  construction site (tunnel lining rings, scaffolding gantries, rails and
  sleepers, lamps, hook and workers with hard hats; vector, with a hand-drawn
  wobble), drawn stroke by stroke in four batches over about 18 seconds so the
  page fills progressively. It replaced the photo-derived line art (unclear and
  fuzzy), so the Unsplash photo and its credit are **no longer used**; the
  drawing is our own artwork and may live in the public repository. The
  approved logo; "Launching soon..." in **bold**, sentence case, logo orange,
  **typed letter by letter** (fast: about 0.13 s per letter, done in about
  4 seconds; smaller than first drafted, clamp 15 to 27 px); the pencil is a
  lighter grey (`#9199a1`); "EMPLOYEE" / "ZONE" in
  **capitals**, two lines, borderless, top-left, the logo's blue (`#1F72C4`),
  with "Employee" condensed to the width of "Zone" (Zone keeps natural
  spacing); reduced-motion fallback. Prototype, screenshots and the generator
  are in `assets/landing-prototype/` (private; `index.html` opens in any
  browser). Build the real page from it.
- **DNS (checked 20 November 2026):** `www.example.com` and the bare
  `example.com` have **no records** and there is no wildcard. The owner adds at
  the registrar's DNS (the registrar): `www` A 203.0.113.10 and, optionally, `@` A
  203.0.113.10 to redirect the bare domain to www; short TTL (300). The proxy
  then issues the HTTPS certificates itself. **No `test-www` (owner, same
  day):** on the test site the landing page is served by `test.example.com`
  itself at the front path `/`, in front of the existing test portal (every
  other path unchanged); "Employee Zone" leads to the portal sign-in. This
  matches the end design where one host is both landing page and portal.
- **Scheduled (owner, 20 November 2026):** P55 then P47 start at 05:40 IST on
  20 November without asking again (session-scheduled; if the session was not
  running, it did not fire). P47 goes to production only if the `www` record
  resolves.
- Tools: nothing to install to manage it. The site is plain files in the
  repository, edited with any text editor and an image editor, and deployed
  like the other modules. A content-management system would only be added if
  non-technical people must edit pages later.
- Owner to supply: logo file and background image (or tell me to pick a
  licence-free one).

### P53 — Desk: day-planning widgets and dashboards from all apps

**App:** portal · **Also touches:** signin, mail, drive, dms · **State:** in progress

**Status:** parked, owner request 20 November 2026; **do not start now**, take up later when the owner says (planning not started). After
sign-in the portal's Desk becomes the user's quick day-planning page:
widgets and dashboards with data from all apps (for example approvals waiting,
today's assignments and tasks, unread mail, chat mentions, recent Drive files,
DMS items to act on, key ERP figures). Apps connect to the Desk rather than to
the public landing page (P47). Rules: each widget calls the app's API with the
person's own session, so the server decides what they may see; widgets differ
by role; the phone's "Today" dashboard (P50) should use the same data sources
so both devices agree. To settle with the owner: which widgets first, layout,
refresh behaviour, and how widgets are added per module.

**Additional scope (owner, 20 November 2026):**
- **Universal alerts:** collect alerts and notifications from all apps (ERP,
  HR, Drive, Mail, DMS, chat, sign-in) into one place on the Desk, per person
  and permission-filtered, with read/unread and a link to the item.
- **Universal search:** one search box that searches across all installed apps
  (ERP records, Drive files, mail, DMS documents, chat) with the person's own
  access, and shows results in one list with the source app.
- **One ecosystem:** instead of going into each app to find something, the
  person sees and acts on the important things from the Desk (dashboard
  widgets, alerts, search), so the apps behave like one system. Same data
  sources for the phone app's Today screen (P50).

**Additional scope (owner, 21 November 2026): one universal sign-out on the ezone
page.** The portal page (now called **eZone**, see P60) gets a single **Sign out**
control that ends the user's single sign-on session everywhere, and the sign-out items are
**removed from every individual app** (ERP Desk user menu, Drive, Mail, DMS, Raven and
Insights menus, and the editor). Design notes to settle at planning:
- The control runs the existing global logout (`finish_logout`, authentik logout flow,
  then the landing page, P56) so it ends the sign-in service session and every app session
  (ERP, Drive, Mail, DMS, ONLYOFFICE); the next sign-in needs a fresh passkey (P08).
- Removing the per-app items hides the UI (overlay scripts and settings, in the repository);
  the apps still obey a sign-out coming from the single sign-on side, so the shared-browser
  guard and the idle logout keep working.
- Apps opened outside the portal (direct links, desktop and phone clients) have no sign-out
  item: show a way back to eZone, keep session expiry, and give the mobile app (P50) its own
  universal sign-out. Decide the behaviour for unsaved work in open frames (warn before
  signing out), for shared computers, and for audit (who signed out, when).
- Sits with the alerts, universal search and widgets of this item; stays **parked** until
  the owner says to start.

**Moved to P82 (owner, 25 November 2026):** the mobile app's universal sign-out (signing out
in the app signs the person out of the Desk and all apps), the limit of one phone and one
computer session per user, and the 30-minute inactivity sign-out. The Desk sign-out control
and removing the per-app sign-out items stay here.

**Additional scope (owner, 26 November 2026): an alerts and exceptions widget for the sign-in admin.** The person
with authentik admin rights has a widget on their Desk showing the system's alerts and exceptions: monitoring and
backup alerts (P72), and the sign-in exceptions of P82 (keys removed for no use, erases after wrong attempts,
pending or refused onboardings, unknown computers, failed certificate checks, and sign-ins from unusual places or
networks). Shown only to that role; each item
links to where it is handled. The admin also receives these alerts directly (owner).

**Taken up (owner's go, 27 November 2026): only the admin alerts widget and a monitoring links panel; everything else
in P53 stays parked.**
- **Alerts widget:** for the admin role only. It shows open alerts from P72's inbox, newest first, read or unread,
  each linked to where it is handled.
- **Links panel** (owner: yes): Grafana (disk, memory, CPU, containers, logs), TrueNAS, Coolify (production and test)
  and Frigate.
  - The panel says these are reachable only over the tailnet and use their own administrator sign-in until P102.
  - The addresses come from the deployment profile, not the code.

**Taken up (owner's go, 27 November 2026): help, notifications, search and sign-out move from the apps to the Desk.**
These four leave every app's own screen and become universal on the Desk; the day-planning widgets stay parked.
- **Owner's decisions (27 November 2026):**
  1. **How the Desk asks each app:** through the app's own script of ours in a background frame, with the person's
     existing session, so each app decides what the person may see. The ERP server gets no per-person keys to the
     other apps.
  2. **DMS notifications:** "documents in your inbox" and "failed imports" (the DMS has no per-person feed).
  3. **Help:** one Desk help page with a short guide per app; "Report a problem" (P107) plugs in later and stays
     parked.
  4. **Apps opened outside the Desk** (direct links, desktop and phone clients): a "back to eZone" link, no
     sign-out or help item.
  5. **Unsaved work:** warn before signing out when an app has an open editor or draft.
- **Build order:** sign-out, help, notifications (grouped by app), search (one box, results show the app).
- **Where the four sit (owner, 27 November 2026):** at the top right of the Desk, sign-out last.
- **Step 1 (sign-out):** public draft #142; not yet on the test site.
- **Read-only check on the test site (27 November 2026, test ERP at `5cc6d1a`; nothing changed):**
  - **ERP** (Frappe 16.60.2): global search answers and is permission-aware (32 record types indexed); the
    notification list has read, unread and mark-as-read calls. The help menu's three items can be hidden in
    Navbar Settings. "Log out" is not listed there in version 16, so our session script hides it.
  - **Insights:** no search or notifications of its own; dashboards, workbooks and queries are ERP records, found
    by name.
  - **Drive** (ownCloud Infinite Scale 8.2.3): the search, notification and live-event services run. **Content
    search is off** (no text extractor configured): search finds names and tags only. Turning it on means pointing
    Drive at the Tika service we already run, and a re-index. **Owner (27 November 2026): turn it on**, as its
    own change, tested first.
  - **Mail** (Stalwart 1.1.1, webmail 1.21.2): the mail interface answers; the webmail has its own search,
    notification centre, help links and shortcuts screen, in source we already build from.
  - **DMS** (Paperless-ngx 3.4.2): a global search call exists; inbox counts and import tasks exist; no
    notification feed (confirmed).
  - **Office editor** (ONLYOFFICE 10.0.0): opens inside Drive; only its help and About entries are affected.
  - **Not checked:** a signed-in person's calls through the frames (needs the bridge first), and the menu items
    in a real browser.
- **Overlap:** public #134 (admin alerts, draft) also changes the Desk page's code file; the two are reconciled
  when the second one is ready.

**Step 1 on the whole test site (28 November 2026):** the combined test build `70636f4` (public #142 with #134 and #69)
puts the Desk bar and sign-out on the test ERP and the matching scripts into test Drive, DMS and webmail; every site
serves the new code (receipt `p53-p72-p69-test-combined-70636f4`). The bar shows on the Desk home only (owner's
correction). Open: the owner's browser check. On test the Desk's sign-out cannot prove Drive, Mail and DMS are signed
out, because they use the production sign-in service; that is checked on production after promotion. Drive content
search (owner: turn it on) is not started.

**Additional scope (owner, 28 November 2026): the dashboards are organised into nine.** Parked with the rest of the
day-planning widgets; not started, nothing designed yet.
- The dashboards are grouped into **nine dashboards**, and **each one is visible to a person according to that
  person's access**: someone without access to an area does not see its dashboard.
- The nine, in the owner's order and with the owner's names:
  1. Acts, Taxes
  2. Fin, AP, AR
  3. HR, PR
  4. Assets
  5. Proc, Inv
  6. Production
  7. Prod, Sales
  8. Budget, Proj
  9. IT Admin
- Six of the names are the same as the head-office spaces in Drive since 28 November 2026 ("Acts, Taxes",
  "Fin, AP, AR", "HR, PR", "Assets", "Proc, Inv", "Prod, Sales"), so a department finds its files and its
  figures under one name. "Production", "Budget, Proj" and "IT Admin" have no Drive space of that name.
- **To settle with the owner at planning:** what each of the nine shows; what "access" is decided by (ERP roles, Drive
  space membership, or groups in the sign-in service); what "Prod" stands for in "Prod, Sales" next to the separate
  "Production"; whether "IT Admin" is the admin alerts widget and links panel already taken up above, or a
  dashboard beside them; and how this fits the existing rule that each widget asks the app with the person's own
  session.
