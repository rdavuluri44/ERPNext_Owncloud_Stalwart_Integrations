# Mobile app (`mobile-app`)

Native iOS and Android app (Expo, React Native) for the ERP: passkey sign-in, role-filtered menus,
read-only lists and records, app lock, tablet split view and an outdoor (sunlight) mode.

## Purpose

Gives staff the ERP on their phone or tablet with the same identity and permissions as the web portal.
The app holds no business rules: every request runs as the signed-in user, so ERPNext decides what each
person may see or do, exactly as on the web.

- **Sign-in:** authentik passkey in the phone's own browser, then ERPNext OAuth with PKCE S256. There is no
  client secret in the app. The server binds the app's tokens to the browser sign-in (`portal/mobile.py`),
  so signing out on the web also ends the app's access.
- **App lock:** Face ID, fingerprint or the phone passcode on every start and after 60 seconds in the
  background; a blank cover hides data in the app switcher.
- **Home:** the menus the user's own roles reach, from `onboarding/api.py` `bootstrap`; lists and records are
  built from ERPNext's own DocType metadata.
- **Sunlight first:** light theme with at least 7:1 contrast, large text and 48 dp touch targets, status shown
  with icon and text, Indian number format (1,50,000.00). Tablets get a list and detail side by side.

Not built yet: field attendance with offline capture, approvals with push notifications, Live Activities.
The Approvals and Inbox tabs are placeholders until then. **What comes next, and how it is built, is in
[`BUILD-GUIDE.md`](BUILD-GUIDE.md)** (owner decisions of 22 November 2026, rules, agent workflow, data paths,
phases).

## Contents

- `mobile/**`: the Expo project (`src/` screens and logic, `scripts/` checks, `assets/` placeholder icons),
  `BUILD-GUIDE.md` (the build guide for agents and developers).
- `tests/test_mobile_app.py`: tenant-neutral source and server API checks.

## Requirements

Modules: `portal-sso` (native login binding and the Bearer gateway route `cloud-raven-native.yaml`),
`onboarding` (the `bootstrap` API).

Node 22 or later and pnpm 10. Expo Go for quick tests; a development build (EAS) for Face ID on iPhone,
push notifications and store releases.

## Reuse

1. In ERPNext, create an **OAuth Client** for the app (app name `ERP Mobile`): grant type Authorization Code,
   response type Code, token endpoint auth method None, redirect URI `<APP_SCHEME>://oauth/callback`. Add its
   ID to the site setting `cloud_native_mobile_clients` (with `cloud_raven_mobile_enabled`) so
   `portal/mobile.py` accepts it.
2. While the app is under test (P38), keep it off production and list it in the private test profile's
   `test_oauth_clients` with `"native": true`, a fixed `client_id`, `"skip_authorization": true` (no
   "allow this app" screen for your own app) and the Expo Go redirect addresses
   (see `deployment/test-runtime.example.json`). Every test bootstrap then creates the client if it is
   missing, restores its redirect addresses and makes it the only native client the test site accepts. The
   test ingress (`tools/prepare_ingress.py`) carries production's native routes (`cloud-raven-native.yaml`).
3. Copy `mobile/.env.example` to `mobile/.env` and fill in your values, then:

```bash
cd mobile
pnpm install --frozen-lockfile
pnpm start        # scan the QR code with Expo Go
```

## Configuration

`mobile/.env` (ignored by Git; none of these is a secret, they belong to one deployment):

| Setting | Used for |
| --- | --- |
| `APP_NAME`, `APP_SLUG`, `APP_SCHEME`, `APP_ID` | App name, Expo project, link scheme for the sign-in return, iOS bundle / Android package ID (`app.config.ts`) |
| `EXPO_PUBLIC_ERP_URL` | The ERP address, for example `https://erp.example.com` |
| `EXPO_PUBLIC_OAUTH_CLIENT_ID` | The OAuth Client ID from step 1 of Reuse; empty disables sign-in |

`app.json` keeps neutral defaults. Install scripts stay blocked and new package versions wait three days
(`mobile/pnpm-workspace.yaml`). Add Expo packages with `pnpm exec expo install <package>` so versions match
the SDK.

## Tests

- `tests/test_mobile_app.py` (offline, part of `python tools/run_unit_tests.py`)
- In `mobile/`: `pnpm typecheck`, `pnpm lint`, `pnpm test` (sunlight contrast 7:1 and Indian number format)

Run these before calling any change done. Real-phone checks are separate: iPhone with and without Dynamic
Island, a recent Android, an older budget Android, a tablet.

## Licenses

The app's own code is part of this repository (AGPL-3.0-or-later). Expo, Expo Router, React and
React Native are MIT; the placeholder icons come from the Expo project template (MIT). See `LICENSES.md`
for the App Store distribution permission.

## AI-assisted development

Written with AI assistance (Anthropic's Claude) and reviewed and accepted by the owner, like the rest of
this repository. `mobile/AGENTS.md` tells AI agents to check the current Expo documentation before
changing Expo APIs.
