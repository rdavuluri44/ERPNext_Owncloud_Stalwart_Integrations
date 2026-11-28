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
- **Foundation (phase 0, no screens yet):** `src/lib/erp.ts` `callErp` checks every ERPNext answer against a
  schema (zod) before use and turns errors into plain messages (`OfflineError`: try later; `ServerError`:
  ERPNext refused, with its own reason). `src/lib/queue.ts` keeps offline requests in order with their client
  ID, so a retry never duplicates; items older than one day are removed; everything is removed at sign-out.
  `src/lib/offline-store.ts` stores the queue in an SQLCipher-encrypted database (key in the Keychain /
  Keystore, this device only) on a development build, and **only in memory in Expo Go**: it writes nothing
  unless encryption is confirmed. Screen texts come from `src/i18n/en.json`.

Not built yet: field attendance with offline capture, approvals with push notifications, Live Activities.
The Approvals and Inbox tabs are placeholders until then. **What comes next, and how it is built, is in
[`BUILD-GUIDE.md`](BUILD-GUIDE.md)** (owner decisions of 22 November 2026, rules, agent workflow, data paths,
phases).

## Contents

- `mobile/**`: the Expo project (`src/` screens and logic, `scripts/` checks, `assets/` placeholder icons),
  `BUILD-GUIDE.md` (the build guide for agents and developers).
- `mobile/trials/passkey-android/`: a throw-away Kotlin test app for P82 (passkeys held by the app, fingerprint
  lock); never shipped, see its README.
- `tests/test_mobile_app.py`: tenant-neutral source and server API checks.

## Requirements

Modules: `portal-sso` (native login binding and the Bearer gateway route `cloud-native-clients.yaml`),
`onboarding` (the `bootstrap` API).

Node 22 or later and pnpm 10. Expo Go for quick tests (iPhone); a development build for the encrypted offline
store, Face ID on iPhone, push notifications and store releases. Android development build on a PC with
Android Studio (JDK 17, Android SDK), installed on the phone over USB:
`pnpm exec expo run:android --device` (the generated `android/` folder stays out of Git). `eas-cli` is pinned
in `devDependencies`: run it as `pnpm exec eas`, never an unpinned `npx`.

**Building the Android development build on Windows** (found on 23 November 2026; the C++ parts, such as the
SQLCipher database, hit Windows' 260-character path limit, which the Android tools do not lift):

1. Work in a short folder, for example a Git worktree: `git worktree add --detach C:\w\erp <branch>`; copy
   your private `mobile/.env` into it.
2. Install with a flat package layout (local only, not committed):
   `pnpm install --frozen-lockfile --config.node-linker=hoisted`.
3. Generate the Android project: `pnpm exec expo prebuild --platform android --no-install` (then undo its
   `package.json` script change with `git checkout -- package.json`).
4. Use CMake 3.31 (its Ninja handles long paths; Windows long paths must be on): install `cmake;3.31.6` with
   the Android SDK manager, and add to `android/local.properties` (generated, not committed):
   `sdk.dir=C\:\\Users\\<you>\\AppData\\Local\\Android\\Sdk` and
   `cmake.dir=C\:\\Users\\<you>\\AppData\\Local\\Android\\Sdk\\cmake\\3.31.6`.
5. Build with Java 17 for your phone's chip only (faster):
   `set JAVA_HOME=<JDK 17 folder>` then `android\gradlew.bat -p android assembleDebug -PreactNativeArchitectures=arm64-v8a`.
6. Install and connect over USB: `adb install -r android/app/build/outputs/apk/debug/app-debug.apk`,
   `adb reverse tcp:8081 tcp:8081`, then `pnpm exec expo start` in the same folder; open the app.
7. Later code changes need no rebuild: update the worktree (`git checkout --detach <commit>`) and the app reloads.
   Rebuild only when native packages or `app.json` plugins change.

## Reuse

1. In ERPNext, create an **OAuth Client** for the app (app name `UNformat ERP`): grant type Authorization Code,
   response type Code, token endpoint auth method None, redirect URI `<APP_SCHEME>://oauth/callback`. Add its
   ID to the site setting `cloud_native_mobile_clients` (with `cloud_native_mobile_enabled`) so
   `portal/mobile.py` accepts it.
2. While the app is under test (P38), keep it off production and list it in the private test profile's
   `test_oauth_clients` with `"native": true`, a fixed `client_id`, `"skip_authorization": true` (no
   "allow this app" screen for your own app) and the Expo Go redirect addresses
   (see `deployment/test-runtime.example.json`). Every test bootstrap then creates the client if it is
   missing, restores its redirect addresses and makes it the only native client the test site accepts. The
   test ingress (`tools/prepare_ingress.py`) carries production's native routes (`cloud-native-clients.yaml`).
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
- In `mobile/`: `pnpm typecheck`, `pnpm lint`, `pnpm test` (sunlight contrast 7:1, Indian number format, and
  the Jest suites in `src/**/__tests__/`: server client, offline queue, encrypted store, texts)

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
