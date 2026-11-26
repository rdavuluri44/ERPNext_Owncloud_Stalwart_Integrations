# Frigate network video recorder (trial)

## Purpose

Record IP cameras on a TrueNAS server with Frigate, which also detects people
and vehicles in the video. This module is the trial stage of P46: one camera on
the local network, recordings in their own capped dataset, the web page with
its login reachable only on the local and private networks, never from the
internet.

## Contents

- `config.yml`: Frigate settings (login on, no MQTT, detection with OpenVINO on
  the processor, 3 days of continuous recording, 14 days of alerts, detections
  and snapshots). It has no cameras until one is installed.
- `../../tests/test_frigate.py`: checks the settings and the version pin.

## Requirements

- TrueNAS with the official catalogue app **Frigate**, image
  `ghcr.io/blakeblackshear/frigate:0.18.3` at digest
  `sha256:d1a3e0008557bb3f3314d442ecd4ba68e9b16ab7872d64612649f7a6e5156635`
  (the standard image, which includes OpenVINO). **0.18.3 is the minimum**:
  it fixes GHSA-7822-v38f-8p44, a critical flaw that allowed remote code
  execution without a login, and the earlier 0.18.2 fixes.
- A dataset for the app, with a quota, separate from backups and virtual
  machines, for example `POOL/nvr` with `config` and `media` folders.
- A camera with an RTSP stream, ideally H.264, with a separate smaller stream
  for detection.

## Reuse

1. Create the dataset and its two folders, and set a quota (the trial uses 100 GiB).
2. Install the catalogue app with: the standard image; config and media as host
   paths on that dataset; **only the web port 8971 published** (it requires a
   login). Do not publish port 5000 (no login), nor 8554, 8555 or 1984 unless
   a feature needs them.
3. Put `config.yml` in the config folder and start the app.
4. Read the first administrator password from the app log in the TrueNAS
   screen yourself, sign in and change it. Do not copy the log anywhere.
5. Do not create viewer accounts while advisories without a fix remain open for
   the viewer role (see below).

## Configuration

Add a camera under `cameras:`, with the password in an app environment variable
such as `FRIGATE_CAM1_PASSWORD`, never in the file. A camera account with
view rights only is safer than the camera's administrator. For an Annke I51DS
(Hikvision-style paths; some firmware uses `/h264/0/main/av_stream` and
`/h264/0/sub/av_stream` instead):

```yaml
cameras:
  cam1:
    ffmpeg:
      inputs:
        - path: rtsp://{FRIGATE_CAM1_USER}:{FRIGATE_CAM1_PASSWORD}@CAMERA_ADDRESS:554/Streaming/Channels/101
          roles: [record]
        - path: rtsp://{FRIGATE_CAM1_USER}:{FRIGATE_CAM1_PASSWORD}@CAMERA_ADDRESS:554/Streaming/Channels/102
          roles: [detect]
    detect:
      width: 640
      height: 360
      fps: 5
```

Detection runs on the small stream; the main stream is recorded as it arrives,
without re-encoding. A host with an Intel graphics chip or an Intel Arc card can
set `device: GPU` and hardware decoding instead.

**Security.** Frigate published many advisories in 2026, several critical.
Keep to the newest release, and watch it daily (`frigate` in
`deployment/upstream-watch.json`). As of 26 November 2026, GHSA-c4qf-xxq4-vf55,
GHSA-74x4-gw64-2mq5, GHSA-mgh5-cr9h-g6hr, GHSA-4xp7-86rr-9758 and
GHSA-w3c4-957q-2jw4 list no fixed version; the first three need a signed-in
viewer, so the trial has the administrator only.

## Tests

Run `python3 tests/test_frigate.py` from the repository root (needs PyYAML).
On the host, check that the app shows version 0.18.3, that the web page asks
for a login, that port 5000 is not reachable, and that recordings appear in the
media folder once a camera is added.

## Licenses

Frigate is MIT-licensed (© Blake Blackshear and contributors; checked at
v0.18.3, 26 November 2026). The optional paid Frigate+ model service is not
used. The bundled SSDLite MobileNet v2 model comes from Intel's Open Model Zoo.
This module's own files use the repository license.

AI-assisted development by Claude (Anthropic).
