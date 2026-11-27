# Passkey trial for Android (P82, first step)

A small throw-away test app in Kotlin. It is **never shipped** and is not part of the mobile app's build. It
answers the three open questions of P82 before anything is built into the real app:

1. Does a computer's QR sign-in accept passkeys held by our own app (a third-party passkey service on Android 14+)?
2. What works on Android 9 to 13, where Android has no passkey services?
3. Does the fingerprint lock behave correctly on the phone brands in use: the key signs only after a strong
   fingerprint or face match, there is no PIN fallback, and adding a fingerprint or face destroys the key?

## What it does

- **Fingerprint-lock test** (Android 9+): makes a key in the phone's secure hardware (`Keys.kt`), reads back what
  the phone really did, and **refuses** the key when the phone gave less than asked (not in secure hardware, no
  match needed, not destroyed on a new fingerprint, or not limited to strong biometrics). "Sign again" after
  adding a fingerprint must report the key as destroyed.
- **Passkey service** (Android 14+, `TrialProviderService.kt`): the phone offers "Passkey trial" next to its other
  passkey services. Making a passkey creates such a key; signing in asks for the fingerprint once and signs. The
  key never leaves the phone and is never marked as backed up.
- **Own QR route** (all Android versions, `Hybrid.kt`, `HybridActivity.kt`): "Scan a computer's QR code" reads
  the sign-in QR code a computer's browser shows, opens a tunnel at a relay server, announces the phone over
  Bluetooth, agrees an encrypted channel with the computer (the public FIDO standard, CTAP 2.2 hybrid
  transport) and answers the request after a fingerprint match with the same hardware key. It can make a
  passkey and sign in. It does not use Android 14's passkey services, so it also runs on Android 9 to 13.
- **Log** on the screen and in `adb logcat -s PasskeyTrial`: who called (browser, Google Play services for the QR
  route, or an app), whether Android verified it, and the result. The log holds no secrets and no site or user
  names (those are shown on the screen only): private keys stay in the secure hardware, and the trial is used
  against a public passkey demo website only.

## Who the app answers (fixed after the review of 26 November 2026)

- **A verified browser** (Android checked the caller against Google's public list of browsers; Google Play
  services, which carries a computer's QR sign-in on Android 14+, is on it). Only such a caller's client-data
  hash is ever signed, and only for its own website's key.
- **The app itself.** It names no website, and the app writes the client data itself.
- **Nobody else.** An app that claims a website without being verified, and every other app on the phone, is
  refused before any key is made or any fingerprint is asked (`WebAuthn.callerAllowed`, `Caller.kt`). Without the
  browser list (no internet at first start) every caller is refused.

## Trial-only shortcuts (do not copy into the real app)

- The browser list is fetched from Google at start and not pinned.
- A website's key name is checked against its host, but two-part public endings (such as `co.uk`) are not known
  to the app; it relies on the verified browser, which refuses them before it calls.
- The encryption building blocks of the own QR route (key derivation, the handshake, point decoding, the data
  reader) are written by hand and unit-tested, not taken from reviewed libraries. The real build replaces them
  where a reviewed library exists.
- The QR reader is Google's and needs Google Play services.
- The own QR route uses the public relay the standard assigns number 0 (run by Google), without any agreement
  with its operator; the relay sees only encrypted bytes. Owner's decision (26 November 2026): the real app
  uses this relay too, until the own QR route is retired (when no phone below Android 14 is left).
- The own QR route is not security-reviewed. Owner's decision (26 November 2026): Codex reviews it, in the role
  of a senior security analyst, before any real sign-in (planned for the week of 30 November 2026; P82).
- No sign counter, one fixed test identity (AAGUID), debug signing.
- Library checksums are not pinned (the real app pins them).

## Build and run

Needs JDK 17, the Android SDK (platform 36) and Gradle 9.4 or newer. No Gradle wrapper is committed.

```
cd mobile/trials/passkey-android
gradle testDebugUnitTest assembleDebug
adb install -r build/outputs/apk/debug/passkey-trial-debug.apk
```

On the phone: open **Passkey trial**, run the fingerprint-lock test, then (Android 14+) switch the service on with
"Open the phone's passkey service settings" and use a public passkey demo website in the phone's browser and on a
computer (QR).

## Tests

`gradle testDebugUnitTest` runs `WebAuthnTest` and `HybridTest` on the computer: the byte formats (CBOR against the standard's
examples, the public key, the signed data, attestation), the rule that a website may use only its own key, and the own QR route's parts (QR decoding, key
derivation against the standard's example, the Bluetooth advert, the relay names, and a full handshake between
a simulated computer and the phone side, including a stranger and a replay being refused).
`tests/test_mobile_app.py` checks that the trial stays neutral and keeps its lock rules. The phone results are
recorded by hand in the P82 record.

## Licences

Our own code, AGPL-3.0-or-later like the repository. Libraries: `androidx.credentials` 1.6.0 and
`androidx.biometric` 1.1.0 (Apache-2.0, Google), OkHttp 4.12.0 (Apache-2.0, Square) for the relay connection,
Google's code scanner `play-services-code-scanner` 16.1.0 (Android Software Development Kit licence) for reading
the QR code, JUnit 4.13.2 for tests (EPL-1.0). The passkey service follows Google's public Credential Manager
documentation; no code was copied from the sample apps. The own QR route was written from the public standard,
with the hybrid authenticator of microG GmsCore (Apache-2.0, https://github.com/microg/GmsCore,
`play-services-fido`) as the reference for the message layouts; no file was copied.

## AI-assisted development

Written with Claude Code and checked by the developer.
