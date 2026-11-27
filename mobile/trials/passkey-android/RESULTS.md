# P82 trial results

Results of the trial app in this folder on real phones. Each line comes from the app's own log. Status: **in
progress** (26 November 2026); the P82 record is updated from this file when the trial is complete.

## Question 3: does the fingerprint lock behave correctly?

### Samsung Galaxy F22 (SM-E225F), Android 13 (API 33), no StrongBox chip, Google Play services 26.45

| Check | Result |
|:--|:--|
| Key made inside secure hardware | Yes (trusted environment; this phone has no StrongBox chip) |
| A match is needed for every signature, enforced by the hardware | Yes |
| Strong biometrics only, no PIN fallback | Yes |
| Signs after a fingerprint match | Yes (twice) |
| **Adding** a fingerprint destroys the key | **Yes**: "Sign again" reported the key as destroyed, without a prompt |
| **Removing** a fingerprint destroys the key | **No**: the prompt appeared and the key signed with a remaining finger |
| Fingerprints enrolled before the key was made | All of them open the key (three people's fingers were enrolled) |

### Oppo CPH2525, Android 15 (API 35), no StrongBox chip, Google Play services 26.45

| Check | Result |
|:--|:--|
| Key made inside secure hardware, match needed for every signature, strong biometrics only | Yes (the reported rejection of the lock flag on Oppo phones did not occur on this model) |
| Signs after a fingerprint match | Yes |
| **Adding** a fingerprint destroys the key | **Yes** |

## Question 1: does a computer's QR sign-in accept passkeys held by our own app?

**Yes** (Oppo CPH2525, Android 15; a Windows 11 computer with Bluetooth, Chrome; a public passkey demo website).

| Step | Result | Who called the app (from the log) |
|:--|:--|:--|
| The phone lists the trial app as a passkey service and lets it be switched on | Yes | - |
| Make a passkey in the phone's Chrome, saved in the trial app | Accepted by the website | Chrome, stating the website; on Google's browser list |
| Sign in with it in the phone's Chrome | Signed in | Chrome |
| Sign in on the computer: QR code scanned with the phone's camera, Bluetooth on both | **Signed in on the computer** | **Google Play services** (`com.google.android.gms`), stating the website and supplying the hash; it is on Google's browser list, so the app can verify the caller |

The key was the fingerprint-locked hardware key throughout (one fingerprint match per sign-in). Attestation was
"none" in these runs; Android key attestation is not tested yet.

## Question 2: what works on Android 9 to 13?

Tested on the Samsung Galaxy F22 (Android 13, API 33). Status: **the standard route does not exist there; our own
route works (see below).**

| Step | Result |
|:--|:--|
| Fingerprint-locked hardware key (question 3) | Works (see above); the lock itself needs only Android 9 |
| Passkey service settings | None: the phone has no such settings page, so the trial app cannot be switched on |
| Make a passkey on the demo website in the phone's Chrome | The sheet offers **only Google Password Manager** (the phone's Google account) and "Use a different device"; the trial app is not offered. Cancelled, nothing saved |
| Computer QR sign-in with a key of our app | Not possible by the standard route: Google Play services answers the QR and knows only Google's own passkeys on this Android |

What this means: on Android 9 to 13 the app can hold the fingerprint-locked key and use it for **its own**
sign-in (the app talks to the sign-in server itself), but websites in the phone's browser and a computer's QR
sign-in cannot reach that key through Android. The own route is researched below.

### Research (26 November 2026, public sources; nothing built or tested): the app runs the QR step itself

**Finding: technically possible, also on Android 9 to 13, but a large and security-critical piece of work.**

- **How:** the person taps "Scan computer QR" in our app; the app reads the computer's QR code, announces
  itself over Bluetooth so the computer knows the phone is nearby, opens an encrypted tunnel to the computer
  through a relay server, receives the sign-in request, asks for the fingerprint and signs with the hardware
  key. This is the public FIDO standard (CTAP 2.2/2.3 "hybrid transport"), the same one Google Play services
  runs on newer phones; the computer's browser needs no change.
- **Phishing protection stays:** the computer's browser puts the real website's identity into the encrypted
  request and the Bluetooth step proves the phone is nearby. This is why it differs from the own QR approval
  that was refused in P82 (option B).
- **Android needs:** Bluetooth advertising (in Android since version 5), camera, internet. Nothing from
  Android 14. The same route would also work on newer phones.
- **Existing open code (checked on GitHub, 26 November):**
  - microG GmsCore (Apache-2.0, about 15,400 stars, active): the phone side in Kotlin
    (`play-services-fido/.../hybrid/`). The best reference; its licence allows reuse with credit.
  - kanidm webauthn-rs (MPL-2.0, active): both sides in Rust and a relay server (`cable-tunnel-server`).
  - LibreCaBLE and fidont (GPL-3.0, each about a month old, a dozen stars, self-described as experimental and
    not audited): proof that a third-party app can do it; not a base to build on.
- **The relay server** (decided on 26 November 2026, see "Owner's decisions" below). The phone names the relay. Either Google's public one (works
  today according to these projects, but we have no agreement with Google and it could be closed to us), or
  our own relay on a domain name that the standard derives from a number (must be registered and run by us;
  code exists in webauthn-rs).
- **Cost and risk:** estimated 4 to 6 weeks including tests, plus an outside security review, because it is
  encryption protocol code where a mistake breaks sign-in security. None of the open implementations is
  certified.
- **Options for the owner** (the owner chose option 2 on 26 November 2026):
  1. Older phones use the app only; signing in on a computer needs a phone with Android 14 or newer.
  2. Build the own QR route (above), for all phones.
  3. Decide after counting how many people need computer sign-in and carry a phone below Android 14.

## Open points found by the trial (to solve later)

### Own QR route on a real phone and computer (26 November 2026): it works on Android 13

Built into the trial app after the owner's go ("Scan a computer's QR code") and run on the Samsung Galaxy F22
(Android 13, where the standard route does not exist) against Chrome on a Windows 11 computer and a public
passkey demo website, through the standard's public relay number 0.

| Step | Result (from the phone's log) |
|:--|:--|
| Read the computer's QR code in the app | Yes (the first try failed only because the phone was still downloading Google's QR reader part) |
| Connect to the relay, announce over Bluetooth | Yes, within a second |
| Encrypted channel agreed with the computer | Yes, about 3 seconds after the scan |
| **Make a passkey** asked by the computer | **Accepted by the website**; key in secure hardware with the full fingerprint lock |
| **Sign in on the computer** with that key | **Signed in** after one fingerprint match |

Notes: after its answer was accepted, the computer sent one more request with command number 0, which the app
refused as unknown; harmless here, to be understood before real use. The code is a trial: written in one
sitting, covered by unit tests, not security-reviewed, and it uses a relay we have no agreement with. The
review comes before real sign-ins; the relay stays by the owner's decision (see "Owner's decisions" below).

**Answer to question 2:** phones with Android 9 to 13 can sign in on a computer by QR code when the app runs
the route itself. Tested on Android 13 only; Android 9 to 12 are not tested.

### Android key attestation over the own QR route (26 November 2026): produced and not rejected; verification not proven

The "proof of the genuine app" of P82: when a key is made, the secure hardware adds certificates that say the
key lives in real secure hardware and which app asked for it.

| Step | Result |
|:--|:--|
| The Samsung (Android 13) produces the certificates for a fingerprint-locked key | Yes: 4 certificates; the last one is Google's hardware attestation root (serial `f92009e853b6b045`) |
| Sent as `android-key` attestation when a computer asks for a new passkey with attestation "Direct" | Yes |
| The demo website's answer | **Success** |

**What this does not prove:** the demo website does not show whether it checked the certificates, or whether the
computer's browser passed them on unchanged. That can only be confirmed on a sign-in server we can inspect
(the test site: the stored attestation of the new key and the server's log). The Oppo, and the passkey-service
route, are not tested with attestation.

### 1. Removing a fingerprint does not destroy the key

- **What the record says:** "adding or removing one destroys the key" (P82, owner decisions of 25 November).
- **What the phone does:** Android destroys such a key only when a fingerprint or face is **added** (or when the
  last one is removed, or the screen lock is removed). Removing one of several leaves the key valid. This is
  Android's documented behaviour of `setInvalidatedByBiometricEnrollment`, not a fault of the app, and an app
  cannot change it.
- **Risk:** small on its own. Removing never lets a new person in; adding does, and adding destroys the key.
- **Done (26 November 2026):** the P82 record and the decision log now say that only adding destroys the key.

### 2. A strong face unlock already on the phone can open the key, also after all fingerprints are removed

- **Owner's question (26 November):** if the app should accept nothing but the fingerprint, can a good-quality
  face unlock still open it after the fingerprints are removed?
- **Answer:** yes, on the few Android phones whose face unlock is rated "strong" (Class 3; for example recent
  Pixels). Android does not let an app choose fingerprint over a strong face: both are "strong biometrics" and
  the phone decides which to offer. A strong face that was enrolled **before** the key was made opens the key,
  and it keeps doing so after every fingerprint is removed, because a strong biometric is still enrolled. A
  face enrolled **after** the key was made destroys the key, like a new fingerprint.
- **Where it does not apply:** most Android phones (including the two trial phones) have only camera-based
  "weak" face unlock, which can never open the key.
- **Not verified on a phone:** no phone with strong face unlock was available for the trial.
- **Owner's view (26 November): no threat, no exception for such phones.** Whoever removes the fingerprints
  and uses the face is still the person whose face was on the phone at onboarding; nobody new can be added
  without destroying the key. Strong-face phones are therefore accepted like any other (as P82 already says).
- **What remains:** the same as point 3. A second person's face enrolled **before** onboarding (some phones
  allow an alternative look) would open the key, so the project manager's check at onboarding covers the
  enrolled face as well as the fingerprints (the P96 procedure already asks for "only their own fingerprints
  and face").
- **For later:** an automatic "fingerprint only" rule is not possible with public Android functions today (an
  app sees that face hardware exists, `FEATURE_FACE`, but not whether it is rated strong); watch new Android
  releases for a way to name the sensor type.

### 3. People enrolled on the phone before onboarding

- All fingerprints (and a strong face) enrolled before the key is made can use it; the phone never tells an app
  whose finger matched or how many are enrolled.
- Covered today only by the manual check at onboarding (P82, P96). Nothing in software can check it.

### 4. Owner's proposal (26 November): remove keys not used to sign in for 7 days

- **What:** a key that has not signed in for 7 days is removed on the sign-in server; the person onboards again
  (project manager, then admin).
- **What it helps:** limits how long a key stays usable on a phone that left the person's hands, or whose
  enrolled fingers changed in a way the phone does not punish (points 1 to 3). It must run on the sign-in
  server (its record of each key's last use), because a phone that is switched off cannot remove its own key.
- **Cost to weigh:** anyone away for more than 7 days (leave, illness, a site without signal) needs a project
  manager visit and an admin approval again.
- **Status:** decided by the owner on 26 November 2026 and recorded in P82; the admin sets the number of days
  per sign-in group (7 when none is set). Not built.

## After the review fixes (26 November 2026, evening): the routes still work

The review of this pull request found that the passkey service answered callers it had not verified. The app now
answers only a verified browser or itself (see the README, "Who the app answers"); the channel is locked against
two writers; incoming points are checked explicitly; the data reader is stricter; site and user names are out of
the log. Re-test on the Oppo CPH2525 (Android 15) with the fixed build, from the app's own log:

| Route | Result |
|:--|:--|
| Own QR route: make a passkey asked by the computer | Done (a first try was cancelled at the fingerprint prompt and correctly refused) |
| Own QR route: sign in on the computer | Done |
| Android's route (computer QR through the phone's camera) | Done twice; caller Google Play services, `verified=true allowed=true` |
| A sign-in asked when the phone held no passkey for the site | Refused ("no passkey here"), the computer showed an error |

Not tested on a phone: the refusal of an unverified caller itself (it needs a second, hostile app on the phone);
it is covered by the unit test `onlyAVerifiedBrowserOrOurOwnAppIsServed`. The tester also reported a sign-in in
the phone's own Chrome as working; that line was no longer in the part of the log that was read.

Still unexplained: after each accepted answer the computer sends a two-byte message (message type 1, command
number 0, nothing after it), which the app refuses as unknown.

## Owner's decisions on these results (26 November 2026, recorded in P82 and `docs/decisions.md`)

- **Own QR route:** built for all phones, as a temporary add-on. The app reports each phone's Android version, and
  the route is retired when no active phone is below Android 14. It stays a separate, removable part.
- **Relay:** the standard's public relay number 0 (run by Google), for the trial and for real sign-ins until the
  route is retired. No relay of our own. Accepted: no agreement with its operator.
- **Security review:** Codex, in the role of a senior security analyst, before any real sign-in; planned for the
  week of 30 November 2026.
- **Unused keys:** removed by the sign-in server after 7 days, the number of days set per group by the admin.
- **Wording:** the record now says that only adding a fingerprint or face destroys the key.

## Notes for the real app

- The test screen confused the tester: "make a key" answered "a key exists already" instead of simply asking
  for the fingerprint, and the "destroyed" message was below the visible part of the screen. The real app
  must say what happened in plain words at the place the person is looking.
- A first fingerprint prompt was cancelled by accident; the key stayed intact and the next try worked.
