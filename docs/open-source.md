# Open-source projects

> Generated from `docs/open-source.json` by `tools/open_source.py render`; edit the JSON. Every project we
> use, borrow code from or evaluate, with its licence, where we use it and how we track it (P35). Licences
> as read from each repository on the date of the entry; "to verify" where the repository states none.

## In use

| Project | Licence | Used in | Tracked | Note |
|---|---|---|---|---|
| [Frappe Framework](https://github.com/frappe/frappe) | MIT | erp-addon-shell, portal-sso, drive-store | daily watch: `frappe` |  |
| [ERPNext](https://github.com/frappe/erpnext) | GPL-3.0 | erp-addon-shell, custom-hr, onboarding | daily watch: `erpnext` |  |
| [Frappe HR](https://github.com/frappe/hrms) | GPL-3.0 | erp-addon-shell, custom-hr | daily watch: `hrms` |  |
| [India Compliance](https://github.com/resilient-tech/india-compliance) | GPL-3.0 | onboarding | daily watch: `india_compliance` |  |
| [India Payroll](https://github.com/frappe/india-payroll) | GPL-3.0 | erp image | daily watch: `india_payroll` |  |
| [Frappe Insights](https://github.com/frappe/insights) | AGPL-3.0 | insights-adapter | daily watch: `insights` |  |
| [Payment Integration Utils](https://github.com/resilient-tech/payment_integration_utils) | GPL-3.0 | erp image | daily watch: `payment_integration_utils` |  |
| [RazorpayX Integration](https://github.com/resilient-tech/razorpayx-integration) | GPL-3.0 | erp image | daily watch: `razorpayx_integration` |  |
| [Frappe Bench](https://github.com/frappe/bench) | GPL-3.0 | deployment (build) | daily watch: `frappe-bench` |  |
| [frappe_docker (official build recipe)](https://github.com/frappe/frappe_docker) | MIT | deployment | daily watch: `frappe_docker` |  |
| [Frappe Suite app logos](https://github.com/frappe/suite) | AGPL-3.0 | erp-addon-shell | artwork copied once (LICENSES.md); no code runs |  |
| [authentik](https://github.com/goauthentik/authentik) | MIT (core; enterprise features under their own licence) | authentik-identity, portal-sso | daily watch: `ghcr.io/goauthentik/server` |  |
| [ownCloud Infinite Scale](https://github.com/owncloud/ocis) | Apache-2.0 | drive, drive-store | daily watch: `owncloud/ocis` |  |
| [ownCloud Web](https://github.com/owncloud/web) | AGPL-3.0 | drive | shipped inside ownCloud Infinite Scale releases, which are watched | upstream repository archived on 23 November 2026; the web client lives on in ocis (services/web); to verify where development continues |
| [ocis-konnectd](https://github.com/owncloud/ocis-konnectd) | Apache-2.0 | deployment (native clients) | daily watch: `ocis-konnectd` | upstream repository archived since 2020; we pin it for the native sign-in clients |
| [ONLYOFFICE Docs](https://github.com/ONLYOFFICE/DocumentServer) | AGPL-3.0-only with additional terms | onlyoffice-editor | daily watch: `onlyoffice/documentserver` |  |
| [Stalwart Mail Server](https://github.com/stalwartlabs/stalwart) | AGPL-3.0 (or the commercial SEL) | mail | daily watch: `stalwartlabs/stalwart` |  |
| [Bulwark Webmail](https://github.com/bulwarkmail/webmail) | AGPL-3.0-only (integrations/mail/LICENSE.upstream) | mail | daily watch: `bulwark-webmail` |  |
| [Paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) | GPL-3.0 | dms | daily watch: `ghcr.io/paperless-ngx/paperless-ngx` |  |
| [Apache Tika](https://github.com/apache/tika) | Apache-2.0 | document-worker | daily watch: `apache/tika` |  |
| [Gotenberg](https://github.com/gotenberg/gotenberg) | MIT | document-worker | daily watch: `gotenberg/gotenberg` |  |
| [Coolify](https://github.com/coollabsio/coolify) | Apache-2.0 | deployment | daily watch: `coolify` |  |
| [Traefik](https://github.com/traefik/traefik) | MIT | deployment | daily watch: `traefik` |  |
| [nginx](https://nginx.org) | BSD-2-Clause | deployment, website | daily watch: `nginx` |  |
| [Docker Engine (Moby)](https://github.com/moby/moby) | Apache-2.0 | hosts | daily watch: `docker` |  |
| [MariaDB](https://github.com/MariaDB/server) | GPL-2.0 | erp | daily watch: `mariadb` |  |
| [PostgreSQL](https://www.postgresql.org) | PostgreSQL License | dms, identity | daily watch: `postgres` |  |
| [Redis](https://github.com/redis/redis) | AGPL-3.0, RSALv2 or SSPLv1 (Redis 8; we run 8.x) | erp, dms, identity | daily watch: `redis` |  |
| [Python](https://github.com/python/cpython) | PSF-2.0 | erp image, tools | daily watch: `python` |  |
| [Node.js](https://github.com/nodejs/node) | MIT | erp image (build), mail overlay (build) | daily watch: `node`, `node-build` |  |
| [CoreDNS](https://github.com/coredns/coredns) | Apache-2.0 | private DNS | daily watch: `coredns/coredns` |  |
| [Tailscale](https://github.com/tailscale/tailscale) | BSD-3-Clause | hosts (mesh) | daily watch: `tailscale` |  |
| [Linux kernel](https://kernel.org) | GPL-2.0 | hosts | daily watch: `linux` |  |
| [Ubuntu](https://ubuntu.com) | various free licences (Canonical) | hosts | daily watch: `ubuntu` |  |
| [TrueNAS](https://www.truenas.com) | GPL-3.0 (to verify) | backup host, test host | daily watch: `truenas` |  |
| [restic](https://github.com/restic/restic) | BSD-2-Clause | backup | daily watch: `restic` |  |
| [RustFS](https://github.com/rustfs/rustfs) | Apache-2.0 | backup | daily watch: `rustfs` |  |
| [Grafana](https://github.com/grafana/grafana) | AGPL-3.0 | monitoring | daily watch: `grafana/grafana` |  |
| [Loki](https://github.com/grafana/loki) | AGPL-3.0 | monitoring | daily watch: `grafana/loki` |  |
| [Alloy](https://github.com/grafana/alloy) | Apache-2.0 | monitoring | daily watch: `grafana/alloy` |  |
| [Prometheus](https://github.com/prometheus/prometheus) | Apache-2.0 | monitoring | daily watch: `prom/prometheus` |  |
| [node_exporter](https://github.com/prometheus/node_exporter) | Apache-2.0 | monitoring | daily watch: `prom/node-exporter` |  |
| [cAdvisor](https://github.com/google/cadvisor) | Apache-2.0 | monitoring | daily watch: `ghcr.io/google/cadvisor` |  |
| [Expo and Expo Router](https://github.com/expo/expo) | MIT | mobile-app | app dependencies follow the app lock file; not yet in the daily watch (gap, P35) |  |
| [React Native](https://github.com/react/react-native) | MIT | mobile-app | app dependencies follow the app lock file; not yet in the daily watch (gap, P35) |  |
| [React](https://github.com/react/react) | MIT | mobile-app | app dependencies follow the app lock file; not yet in the daily watch (gap, P35) |  |
| [OpenCV (opencv-python-headless)](https://github.com/opencv/opencv) | Apache-2.0 | custom-hr (P95), erp image | already in the ERP image through an upstream app, pinned at 5.0.0.93 in deployment/python-constraints.txt (no advisories, OSV, 26 November 2026); Python packages are not in the daily watch yet (gap) | runs the face models on the server |
| [OpenCV Zoo: SFace and YuNet](https://github.com/opencv/opencv_zoo) | Apache-2.0 (SFace), MIT (YuNet) | custom-hr (P95) | daily watch: `opencv_zoo` | model files pinned by commit and SHA-256 (deployment/face-models.json); SFace training data unverified, asked upstream (opencv/opencv_zoo#313) |
| [Synapse](https://github.com/element-hq/synapse) | AGPL-3.0 | chat | daily watch: `ghcr.io/element-hq/synapse` |  |
| [Matrix Authentication Service](https://github.com/element-hq/matrix-authentication-service) | AGPL-3.0 | chat | daily watch: `ghcr.io/element-hq/matrix-authentication-service` |  |

## Being evaluated or chosen, not in the code yet

| Project | Licence | Used in | Tracked | Note |
|---|---|---|---|---|
| eKYC India | to verify | P03 | — | official source staged, app not installed (P03); record its repository and licence when adopted |
| [frappe_whatsapp](https://github.com/shridarpatil/frappe_whatsapp) | to verify (GitHub reports no standard licence) | P04 | — | planned under P04, not installed |
| [Headscale](https://github.com/juanfont/headscale) | BSD-3-Clause | P29, P82 | — | planned own mesh server (P29); also the later complement for computer binding (P82) |
| [MediaPipe (Face Landmarker)](https://github.com/google-ai-edge/mediapipe) | Apache-2.0 (code and model) | P95 | — | chosen for liveness on the phone; adoption check 26 November 2026 |
| [Silent-Face-Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing) | Apache-2.0 | P95 | — | unmaintained since 2020; one liveness signal only |
| [UniFace](https://github.com/yakhyo/uniface) | MIT (some weights under their own licence) | P95 | — | maintained packaging of the anti-spoofing weights |
| [smallstep step-ca](https://github.com/smallstep/certificates) | Apache-2.0 | P82 | — | chosen for computer certificates (owner, 26 November 2026); advisories to check before adoption |
| [Android identity-samples (MyVault)](https://github.com/android/identity-samples) | Apache-2.0 | P82 | — | structure to borrow for the passkey provider; credit and notice when code is copied |
| [KeePassDX](https://github.com/Kunzisoft/KeePassDX) | GPL-3.0 | P82 | — | reference passkey provider; GPL code only in the public mobile module |
| [Password Store, Passkey Edition](https://github.com/pando85/Android-Password-Store) | GPL-3.0 | P82 | — | reference passkey provider (fork of the archived Android-Password-Store) |
| [React Native VisionCamera](https://github.com/margelo/react-native-vision-camera) | MIT | P95 | — | camera frames for our own MediaPipe plugin |
| [microG (GmsCore)](https://github.com/microg/GmsCore) | Apache-2.0 | P82 | — | reference for the message layouts of the own QR route in the P82 trial app (mobile/trials/passkey-android; written from the public standard, no file copied); its adoption check as a component is still to be recorded in P82 |
| [DB-IP Lite (IP to city database)](https://db-ip.com/db/lite.php) | CC BY 4.0 | P82 | — | one of two free IP location databases for unusual-sign-in alerts; attribution required |
| [MaxMind GeoLite2](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data) | GeoLite2 End User Licence Agreement (free, not an open-source licence) | P82 | — | the other candidate; the format authentik reads natively; needs a free account |
| [AndroidX Credentials and Biometric](https://github.com/androidx/androidx) | Apache-2.0 | P82 | — | P82 trial app (mobile/trials/passkey-android), never shipped; credentials 1.6.0 and biometric 1.1.0, no open advisories (OSV, 26 November 2026) |
| [OkHttp](https://github.com/square/okhttp) | Apache-2.0 | P82 | — | P82 trial app (mobile/trials/passkey-android), never shipped; 4.12.0 for the relay connection, no open advisories (OSV, 26 November 2026) |
| [JUnit 4](https://github.com/junit-team/junit4) | EPL-1.0 | P82 | — | P82 trial app (mobile/trials/passkey-android), never shipped; 4.13.2, tests only |
| [Google code scanner (play-services-code-scanner)](https://developers.google.com/ml-kit/vision/barcode-scanning/code-scanner) | Android Software Development Kit licence (not open source) | P82 | — | P82 trial app (mobile/trials/passkey-android), never shipped; 16.1.0 reads the QR code; needs Google Play services, so the real app needs another reader for phones without them |
| [Pebble](https://github.com/letsencrypt/pebble) | MPL-2.0 | P11 | — | Let's Encrypt's ACME test server, for a local rehearsal of the certificate switch (P11) only; not shipped. v2.10.3 (11 Nov 2026), release checksums verified. |
| [matrix-rust-sdk](https://github.com/matrix-org/matrix-rust-sdk) | Apache-2.0 | P73, P50 | — | Matrix client library for the phone app, through its Kotlin bindings; adoption check passed 27 November 2026 (use 0.20.0 or later) |
| [Ltt.rs](https://codeberg.org/iNPUTmice/lttrs-android) | Apache-2.0 | P109 | — | Android JMAP client; its JMAP library code may be borrowed for the light mail client. Little upkeep (library last changed April 2025), so we maintain our copy |
| [Sygnal](https://github.com/element-hq/sygnal) | AGPL-3.0 | P73 | — | Matrix push gateway for chat alerts on phones; adoption check passed 27 November 2026 (v0.17.0; the matrix-org repository is archived) |

## Used before

| Project | Licence | Used in | Tracked | Note |
|---|---|---|---|---|
| [Raven](https://github.com/frappe/raven) | AGPL-3.0 | erp image | — | removed from the ERP image in P108 (owner, 27 November 2026); Matrix replaces it as the internal chat (P73) |
| [Collabora Online](https://github.com/CollaboraOnline/online) | MPL-2.0 (to verify; GitHub reports no standard licence) | editor | — | used until November 2026, replaced by ONLYOFFICE Docs, P42 |
