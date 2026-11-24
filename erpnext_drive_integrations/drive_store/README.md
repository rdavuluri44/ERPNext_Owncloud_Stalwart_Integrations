# Photo store (`drive-store`, P74)

Work photos from the mobile app, kept in each project's Drive space and reached only through ERPNext.

## Purpose

Site photos (progress, hindrance, incident) taken in the mobile app go straight to the project's Drive
(ownCloud Infinite Scale) space, in a folder per site and date, tagged with project, site, type, time, place,
who took them, "From gallery" and "Captured offline". Receipts, bills and scanned documents are not handled
here: they go to the DMS (Paperless) first.

Owner decisions (24 November 2026):
- **One sign-in.** The phone talks only to ERPNext. ERPNext checks the person's site membership (the same rule
  as attendance, `custom_hr.access`) and the store's own Drive account reads and writes the space. People do
  not need a Drive account to use the photos in the app.
- **Nobody deletes a work photo.** The records cannot be deleted; the store's calls never delete in Drive.
- **Not processed by the DMS.** Project photo spaces must stay outside the document worker: site people get
  no write rights there and the store's Drive account is not enrolled in the worker.
- Archiving old photos is a later item.

## Contents

- `erpnext_drive_integrations/drive_store/**`
- `tests/test_drive_store.py`

Calls for the app (`erpnext_drive_integrations.drive_store.api`):

| Call | Does |
|---|---|
| `upload_photo` (POST, `payload`) | `client_id`, `site`, `kind` (Progress / Hindrance / Incident / Other), `photo` (data URL, under 3 MB; re-encoded, EXIF removed), optional `latitude`, `longitude`, `accuracy_m`, `gps_captured_at`, `from_gallery`, `remarks`, offline fields as in custom_hr. A retry with the same `client_id` returns the same record. |
| `photos` (GET) | The photos the person may see, newest first, 30 at a time: `site`, `project`, `kind`, `day`, `start`. |
| `photo` (GET) | One photo as an image: `size=preview` (256 px from Drive's thumbnail service; needs `256x256` in Drive's `THUMBNAILS_RESOLUTIONS`, set by the Drive stack) or `size=full`. |
| `files` (GET) | Folders and files in a project's Drive space (`project`, `path`), showing only the folders of the person's own sites in that project (as `photos`); empty until the space exists. |
| `file` (GET) | An image from one of the person's site folders in a project's space (`project`, `path`, `size`); other file types open on the web for now. |

Records: **Drive Project Space** (project, Drive space id) and **Drive Photo** (one per photo, with its tags).

## Requirements

Modules: `erp-addon-shell`, `custom-hr` (site membership, photo checks, offline time), `drive` (the Drive it
writes to).

ownCloud Infinite Scale with the auth-app service enabled (`PROXY_ENABLE_APP_AUTH`), reachable from the ERP
server; a dedicated Drive account for the store with the right to create project spaces.

## Reuse

Copy this folder with `custom_hr`; add `drive_store` to the feature list in `hooks.py` and `Drive Store` to
`modules.txt`; set the site configuration below; run `bench migrate`.

## Configuration

Private site config (never in Git) `drive_store`: `url` (internal Drive address), `account` (the store
account's e-mail), `account_id` (its Drive user id), `token` (the first app token, from the CLI enrollment:
`ocis auth-app create --user-name=<account> --expiration=720h`). The token is renewed daily when it ends within
five days; renewed tokens are kept in `sites/<site>/private/drive_store/credential.json` (mode 600). The
feature can be switched off with `cloud_features: {"drive_store": false}`.

## Tests

- `tests/test_drive_store.py` (fake Frappe and Drive): fixed paths, no folder escape, tags, token renewal (same
  account, old token revoked, never on mismatch, no token in errors), access by site membership, idempotent
  upload, no deletes, folder listing, paths that cannot leave the space, project access.
- To prove on the test site: space creation, upload, tags (`/graph/v1.0/extensions/org.libregraph/tags`) and
  previews against the pinned oCIS version; that the document worker does not pick up project photo spaces.

## Licenses

- ownCloud Infinite Scale — Apache-2.0 — https://github.com/owncloud/ocis
- Frappe Framework — MIT — https://github.com/frappe/frappe

This module's code was written with AI assistance (Claude); the maintainers review and test it before use.
