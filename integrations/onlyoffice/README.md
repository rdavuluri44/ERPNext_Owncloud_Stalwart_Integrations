# ONLYOFFICE editor customisation (`onlyoffice-editor`)

Space-saving layout and private sheet views for ONLYOFFICE Docs opened from
Drive through WOPI.

## Purpose

P42: ONLYOFFICE replaces Collabora. In WOPI mode the editor's layout is set by
ONLYOFFICE's WOPI start page (`editor-wopi.ejs`); ONLYOFFICE Community ignores
the official layout options, so our copy of that page applies the layout the
owner agreed on 18 November 2026 (goal: maximum working space).

## Agreed layout (final, owner approved 18 November 2026)

Editor (this module, `editor-wopi.ejs`):
- **One header row:** compact header; Drive's ✕ and ⋮ at the left, then the
  tabs, the file name, and ONLYOFFICE's logo at the far right. The tabs get
  the space first: the file name and the logo shrink (the logo down to its
  icon) before the tabs scroll; the tab scroll arrows are 28 px wide. Avatar, header search, Share and open-file-location are removed (the
  co-editor count appears only while others are in the file).
- **Logo:** kept, as the licence requires, but not linked to the vendor site.
- **Always the light theme** (also on devices in dark mode), so the agreed
  greys, icons and headers look the same everywhere.
- **Tabs start after Drive's ✕ and ⋮** (84 px), which sit at the top left.
- **One side strip, on the right, header grey (#D9D9D9), opened from a
  hamburger (≡) at the far right of the status bar** (after zoom +, like the
  sheet list), on desktop and phones. It takes no width while closed, opens
  over the sheet, and closes with the button or a click on the sheet; it
  stays while one of its settings panels is open. The hamburger is pinned to
  the bottom-right corner above the strip, and one tap closes an open
  settings panel together with the strip. It holds:
  first the contextual settings buttons (cell, shape, image, text, slicer,
  pivot field list: the pivot list and object settings exist only here),
  then the former left strip (search, comments, chat, spell check, about).
  Their panels still open on the left; the empty left column collapses while
  no panel is open. Tried and replaced: always visible, auto-hide on hover,
  an edge handle on phones. Phones use the desktop editor because
  ONLYOFFICE's touch editor is view-only in the free edition (verified on
  10.0.0 build 169).
- **Headers:** row and column headers #D9D9D9, hover #C6C6C6, selected row
  or column #A6A6A6, text #262626; numbers of filtered rows blue (#1F5BC6). The row-number column width is drawn by
  ONLYOFFICE's compiled engine and cannot be changed; white text on the
  selected header is impossible in sheet views (one text colour for all
  headers). Only ONLYOFFICE's official theme tokens are used.
- **Private sheet views:** every person automatically works in their own view
  per sheet ("Private - <name>"), reused on reopening, so filters and sorting
  do not change what others see; protected sheets are skipped; no green
  "Sheet View mode" headers.
  Loop guard (21 Nov 2026): one created view per person, sheet and visit; no second attempt while one is in flight. Before, creating a view fired the sheet-changed event before the rename showed in the list, so another view was created each time (22 "Temporary View N" in one shared workbook). Tested by a headless-Chrome simulation (`tests/test_onlyoffice_private_views.py`). Stray "Temporary View N" views already in a file are removed by hand in View manager.
  Isolation (23 Nov 2026, P61): a private view exists to keep each person's filters and sorting out of
  everyone else's work (others may see the views; their cursors stay visible, they only show where someone
  is). ONLYOFFICE refuses to create or rename a view while another person has View manager open or is
  changing views; the keeper used to try once and give up, leaving the person in the shared Default view.
  Now a refused creation or rename is tried again every 4 s (at most 10 times per sheet and visit; a view
  this visit created is renamed again, never created twice), and a notice with **Back to my view** shows
  when a person stays a few seconds in a view that is not their own (Default or another person's).
  View cap (P61, 22 Nov 2026): no view is added to a sheet that already has 20 views (`MAX_VIEWS`); the person then works in the sheet's normal view, and an existing own view is still used. Tested in the same simulation.
- **Licence notice:** the About panel keeps ONLYOFFICE's notices and adds that
  this is a modified version based on ONLYOFFICE by Ascensio System SIA
  (additional terms 2 and 3). About is the only place these notices appear
  (File → Info is document information), so its strip button stays. About
  shows only when clicked, as a small card (340 px) beside the strip instead
  of a full-window page, with a ✕ close button; Esc or the side-menu
  hamburger also close it.
- **Side-menu hamburger:** four thin lines, matching ONLYOFFICE's sheet-list
  button.
- **Click relay:** a click in the editor tells Drive to close its open file
  menu (no data sent).

Drive (`integrations/drive/workspace.js`, while `/external-onlyoffice/` is open):
- Drive's top bar is hidden; its ⋮ (file menu) and ✕ (close) float in the
  editor's header row at the **top left** (easier to reach on phones):
  transparent, icons rgb(56,56,56), ✕ 24 px icon in a 32 px button at 10 px
  from the left edge, ⋮ 16 px at 46 px.
- **Phones (up to 768 px):** the status bar shows only add sheet (+),
  ONLYOFFICE's sheet list (≡) and our side-menu hamburger; sheet tabs, their
  scroll arrows, zoom and the save-status text are hidden.
- Drive's tooltips are hidden while editing (the ⋮ tooltip stayed on screen).
- Drive's file menu is styled like ONLYOFFICE's (Segoe UI 13 px, dark grey,
  single border, grey hover).
- The editor frame fills the whole window (fixed, edge to edge, no border or
  rounded corners) for a native-app look; Drive's details panel, when
  opened, stays beside it.

Saving: auto-assembly writes changes to Drive every 2 to 3 minutes while open
and within seconds of closing (`deployment/config/onlyoffice-local-production-linux.json`).

## Contents

- `integrations/onlyoffice/editor-wopi.ejs`: patched start page (mounted read-only)
- `integrations/onlyoffice/editor-wopi.original.ejs`: the unmodified page from the pinned image, for review and diff
- `deployment/stacks/editor-onlyoffice.compose.json`, `deployment/config/onlyoffice-local-production-linux.json`
- `tests/test_onlyoffice_editor.py`
- `tools/editor_safety.py`, `integrations/onlyoffice/editor-safety.{service,timer}.example`,
  `integrations/onlyoffice/editor-safety.example.json`, `tests/test_editor_safety.py` (file safety, P61)

## Requirements

ONLYOFFICE Docs 10.0.0 build 169 (package `onlyoffice-documentserver` 10.0.0-169),
pinned by digest. `upstream.json` records the image and the checksum of its own
start page; the tests fail unless the stored original, that record and the image in
`deployment/stacks/editor-onlyoffice.compose.json` agree, so an image change alone
cannot mount the old patched page over a new editor (P91).

## Reuse

Select `editor_product: onlyoffice` in the runtime profile. On an ONLYOFFICE
upgrade (register entries OFFICE-1 to OFFICE-5 in `docs/upstream-customizations.md`):

1. On a host with Docker, run `tools/refresh_editor_original.py --image
   onlyoffice/documentserver@sha256:<new digest> --version "<version> build <n>"`.
   It copies the new image's start page to `editor-wopi.original.ejs` without
   starting the image, and updates `upstream.json`.
2. Re-apply the marked `cloud-integrations` changes to `editor-wopi.ejs` against the
   new original (compare old and new original first).
3. Change the image in the stack and in `deployment/upstream-watch.json`; run the tests.
4. Check whether the sheet-view guard is still needed (below).

## Configuration

Auto-assembly (periodic save to Drive while open) and the WOPI IP filter are
in `deployment/config/onlyoffice-local-production-linux.json`.

## Tests

- `tests/test_onlyoffice_editor.py`
- `tests/test_editor_safety.py` (file safety tool, see below)

## Licenses

- ONLYOFFICE Docs: GNU AGPL v3 with additional terms (attribution, modified
  version notice, no trademark grant), https://github.com/ONLYOFFICE/DocumentServer;
  pinned image, its user interface adjusted at runtime by the start page
  above. The ONLYOFFICE name and logo stay visible; About states the
  modification.
- `editor-wopi.ejs`: Apache License 2.0, (c) Ascensio System SIA; modified
  here (changes marked `cloud-integrations`), notice kept.

Developed with AI assistance (Claude); the owner reviews and is responsible.

Test-site marker: on hostnames starting with `test.` or `test-` (enforced by the renderer) this module shows the shared TEST SITE marker, a 3px striped top line with a small tab, top window only, no layout space. Editor: in the start page, when the office host is opened directly.

## Sheet views that crash the editor (21 November 2026)

ONLYOFFICE 10.0.0 (build 169) can save a sheet view with a column filter that has nothing
inside it (`<columnFilter colId="5" id="{...}"></columnFilter>`). The editor's own
`IU()` method ("is any filter applied") then throws `Cannot read properties of null
(reading 'IU')` when it applies the view; the grid stays blank and the file is unusable for
everyone who opens it. It happened to a shared workbook between 15:32 and 16:16 IST on
20 November (the first save with such a filter is in that window; none before it).

- **Guard** (`SHEET-VIEW-FILTER-GUARD` block of `editor-wopi.ejs`, installed when the editor
  app is ready): replaces `Asc.CT_NsvFilter.prototype.IU` by a null-safe copy, only when the
  loaded build still has the unsafe form, so a fixed upstream build is left alone. Remove the
  guard when the pinned image is upgraded to a build that no longer needs it.
- **Repair tool** (`sheetview_sanitize.py IN.xlsx OUT.xlsx [--temporary] [--drop-all-views]`):
  removes only empty column filters (optionally the empty "Temporary View N" shells, or every
  view as a last resort) and keeps every other byte of the workbook; run it on a copy and upload
  the result as a new file or a new version. `IN.xlsx` alone only reports.
- Tests: `tests/test_onlyoffice_sheetview_filter.py` (reproduces the exact error with the
  editor's original method in headless Chrome).

## File safety (P61)

Aim: a failed save is seen within minutes, no edit is lost, and a stuck file is
recovered without deleting it. Nothing guarantees that a save never fails.

`tools/editor_safety.py` runs as root on the editor's Docker host. It reaches ONLYOFFICE
only through `docker exec` in the editor container: the command service
(`http://localhost/command`), signed with the container's own JWT secret (read from the
container, kept in memory, never printed or put on a command line), and the editor's log
files. It never deletes a parked document or a Drive file.

- `forgotten`: lists the documents ONLYOFFICE parked because their save to Drive failed.
- `rescue`: copies every parked document to the recovery folder (root-only, one folder per
  document key, `manifest.jsonl` with time, size and checksum); content already copied is
  skipped.
- `unstick KEY`: shows how many people have the document open, forces a save to Drive and
  rescues parked edits. With `--yes` it then closes the document for everyone (the next
  opening loads Drive's latest version) and rescues again.
- `watch` (systemd timer every five minutes): counts new editor log lines for failed saves
  to Drive (`PutFile` errors, also from the Drive editor bridge), edits the editor could
  not apply (`changesError`) and parked documents (`storeForgotten`); names the document
  keys concerned; runs the rescue; checks disk use of the editor and Drive volumes
  (alarm at 80 percent) and the editor cache (alarm at 2048 MB). Signals only, delivery
  is P72: exit code 0 fine, 1 a check could not run, 2 an alarm;
  `/var/lib/cloud-editor-safety/status.json`; one journal line per run
  (`journalctl -u editor-safety`).

The cache is not pruned by this tool: ONLYOFFICE deletes cached document folders older than
one day itself every hour (`services.CoAuthoring.expire.files` 86400 s, `filesCron` hourly,
pinned build's defaults). Deleting cache files by hand could destroy unsaved edits.

**Restarts.** The editor container gets five minutes to stop (`stop_grace_period` in
`deployment/stacks/editor-onlyoffice.compose.json`): on every stop the image's own start
script runs ONLYOFFICE's `documentserver-prepare4shutdown`, which saves every open document
to Drive and parks what it cannot save. Docker's default of ten seconds cut it short. For a
host reboot, stop the editor first (`docker stop -t 300 <editor container>`), because
Docker gives containers only fifteen seconds when the host shuts down; see the planned
reboot procedure in `docs/production-moves.md`. The watch rescues anything parked after
the restart.

**Install** (same host as the editor): copy `editor-safety.example.json` to
`/etc/cloud-editor-safety/config.json` and adjust the container prefixes; copy
`editor-safety.service.example` and `editor-safety.timer.example` to `/etc/systemd/system/`
(without `.example`; the service expects the repository checkout in
`/opt/cloud-integrations/repository`); `systemctl enable --now editor-safety.timer`. Make
sure the recovery folder is inside the backed-up area or copied there.

### A file will not open: do not delete it

For everyone: **do not delete the file and do not upload a copy.** Deleting loses its version
history and links; a copy splits the work in two. Close the editor and tell the
administrator the file name and the time.

For the administrator:
1. Look at `/var/lib/cloud-editor-safety/status.json` (or run
   `tools/editor_safety.py watch`): `documents` names the document keys with failed saves or
   edits that could not be applied; the editor log around that time names the file.
2. `tools/editor_safety.py unstick KEY`: forced save and rescue; read what it says.
3. If the file still does not open: `tools/editor_safety.py unstick KEY --yes` closes it for
   everyone (warn the people who have it open), then open it again from Drive.
4. If it still shows a blank grid: in Drive, download the latest version; run
   `sheetview_sanitize.py FILE.xlsx` to see whether it holds the unreadable sheet views; if
   so, `sheetview_sanitize.py FILE.xlsx FIXED.xlsx` and upload `FIXED.xlsx` under the same
   name, so it becomes a new version. A bad save can also be undone by restoring an earlier
   version from Drive's version list.
5. Parked edits rescued into the recovery folder are complete copies of the document as it
   was being edited. Open a copy locally, compare it with Drive's version and decide with
   the owner of the file what to keep. Parked documents stay in the editor until someone
   removes them deliberately; this tool never does.

Tests: `tests/test_editor_safety.py` (a fake Docker plays the editor, with sample log lines
shaped like the incident of 20 November 2026).

