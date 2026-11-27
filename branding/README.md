# Branding

## Purpose

This software ships with its own brand, **Unformat**, as the default look: the "UN / format" logo, the favicon
set and the name shown on the front page. Every deployment can replace it without changing the code (P85).

## Contents

| File | Used for |
|---|---|
| `unformat/logo.svg` | Logo in the ERP and the portal, and on the front page |
| `unformat/favicon.svg`, `unformat/favicon-16/32/48/180/192/512.png` | Browser and home-screen icons |
| `unformat/brand.json` | Name and colours (navy `#1F3A5F`, orange `#E8731A`); the mobile app's name and app ID for later |

The build uses copies of these files in `erpnext_drive_integrations/public/` (`company-logo-approved-v6.svg`,
`company-favicon*.{svg,png}`); the front page takes its default title and name from `brand.json`.

## Requirements

None beyond the deployment module: the files are copied into the ERP build and the front page when the runtime is
rendered (`tools/prepare_runtime.py`, `tools/render_runtime.py`).

## Reuse

Use the folder as a template for your own brand: same file names and sizes, your own artwork.

## Configuration

To replace the branding, keep your files outside this repository (they are your private deployment data) and name
them in the private runtime profile:

1. **Logo:** `"company_logo": "/path/to/logo.svg"` (an SVG).
2. **Favicons:** `"company_favicon_dir": "/path/to/folder"` with all seven files named as above (`favicon.svg`,
   `favicon-16.png` … `favicon-512.png`); an incomplete set is refused.
3. **Front page:** `"website_title"` and `"website_name"`.
4. Render the runtime and deploy as usual (test site first). Your files replace the Unformat ones; nothing else
   changes.

A client's own name, logo, domains and people never go into this repository (see `AGENTS.md`, "Branding and
client identity"); they belong in the private profile.

The mobile app (`mobile/`) does not read `brand.json` yet; its name, app ID and icons follow in a later step.

## Tests

`tests/test_branding.py`: the brand file is complete, the build copies are identical to this folder, the PNGs carry
no metadata, the front page defaults to the brand name, and the copyright and trademark notes are present.

## Licenses

The code in this repository is free software under the AGPL-3.0-or-later (see `LICENSE`). The Unformat artwork is
our own. The name **Unformat** and the "UN / format" logo are trademarks of **unformat.in**. You may use these files
to run, test and show this software. If you ship it as your own product or service, replace our name and logo with
your own using the steps above.

## AI-assisted development

This module was prepared with AI assistance (Claude Code); the maintainers review and stand behind it.
