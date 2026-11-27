// Shared parts of an attendance capture (build guide phase 3): the GPS fix, the times and the photo.
// The server decides everything again (fence, accuracy, time, photo); the app only gathers and pre-checks.
import { File, Paths } from 'expo-file-system';
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';
import * as Location from 'expo-location';
import * as SecureStore from 'expo-secure-store';

import { t as text } from '@/i18n';

/** Phone-local "2026-11-23 08:02:41", as ERPNext writes datetimes (the server's own time zone). */
export function localStamp(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/** ERPNext's "2026-11-23 08:02:41.123456" read as a phone-local time. */
export function parseStamp(value: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})/.exec(value);
  return m ? new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]) : null;
}

// ---- server clock (owner decision 16): offline times are the phone's clock corrected by this difference ----
const OFFSET_KEY = 'server-clock-offset-s';
let offsetS = 0;

/** Remember the server's time minus the phone's, measured from bootstrap's `server_now`. */
export async function rememberServerClock(serverNow: string, phoneNow = new Date()) {
  const server = parseStamp(serverNow);
  if (!server) return;
  offsetS = Math.round((server.getTime() - phoneNow.getTime()) / 1000);
  await SecureStore.setItemAsync(OFFSET_KEY, String(offsetS)).catch(() => {});
}

/** The last measured difference (also after a restart without signal). */
export async function serverClockOffset(): Promise<number> {
  if (offsetS) return offsetS;
  const saved = Number(await SecureStore.getItemAsync(OFFSET_KEY).catch(() => null));
  return Number.isFinite(saved) ? saved : 0;
}

/** The fields an offline capture carries; the server then accepts it for at most a day, marked. */
export async function offlineFields(capturedAt: Date) {
  return { offline: 1, device_captured_at: localStamp(capturedAt), clock_offset_s: await serverClockOffset() };
}

// ---- location ----
export type Fix = { latitude: number; longitude: number; accuracy_m: number; gps_captured_at: string };

/** A fresh GPS fix with its accuracy and time. Refuses a fake ("mock") location on Android. */
export async function getFix(): Promise<Fix> {
  const permission = await Location.requestForegroundPermissionsAsync();
  if (!permission.granted) throw new Error(text('capture.noLocation'));
  const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Highest });
  if (pos.mocked) throw new Error(text('capture.mocked'));
  return {
    latitude: pos.coords.latitude,
    longitude: pos.coords.longitude,
    accuracy_m: pos.coords.accuracy ?? 9999, // sent as measured; the server compares it with the site's limit
    gps_captured_at: localStamp(new Date(pos.timestamp)),
  };
}

/** Metres between two points: the same haversine as custom_hr's `distance_metres` (not rounded). */
export function distanceM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = (d: number) => (d * Math.PI) / 180;
  const h = Math.sin(r(lat2 - lat1) / 2) ** 2 + Math.cos(r(lat1)) * Math.cos(r(lat2)) * Math.sin(r(lon2 - lon1) / 2) ** 2;
  return 6371000 * 2 * Math.asin(Math.min(1, Math.sqrt(h)));
}

export type Fence = { latitude?: number | null; longitude?: number | null; radius_m?: number | null; maximum_accuracy_m?: number | null };

/**
 * What the server will say about this fix, said earlier: the same rule as custom_hr's `validate_location`
 * (accuracy above the site's limit, or farther than the radius; no allowance for accuracy). The server checks
 * again; null when it looks fine.
 */
export function fenceProblem(fix: Fix, fence: Fence): string | null {
  const limit = fence.maximum_accuracy_m || 200;
  if (fix.accuracy_m > limit) return text('capture.poorGps', { accuracy: Math.round(fix.accuracy_m), limit });
  if (fence.radius_m && fence.latitude != null && fence.longitude != null) {
    const d = distanceM(fix.latitude, fix.longitude, fence.latitude, fence.longitude);
    if (d > fence.radius_m) return text('capture.outside', { distance: Math.round(d), radius: fence.radius_m });
  }
  return null;
}

// ---- photo ----
/**
 * Delete the app's own temporary copies; never fails (a missing file is already gone). Only files inside the
 * app's cache folder: a gallery photo's original on the phone is never touched.
 */
export function discardFiles(...uris: (string | null | undefined)[]) {
  let cache = '';
  try {
    cache = Paths.cache.uri;
  } catch {
    return; // no file system (tests): nothing to delete
  }
  for (const uri of uris) {
    try {
      if (uri && cache && uri.startsWith(cache)) new File(uri).delete();
    } catch {
      // already gone
    }
  }
}

/**
 * Shrink a camera photo to about 200 KB and return it as the data URL the server accepts. Both files (the
 * camera's original and the shrunk copy) are deleted at once: photos live only in memory and, unsent, in the
 * encrypted offline queue (rule 7; owner: no phone storage).
 */
export async function photoDataUrl(uri: string): Promise<string> {
  let savedUri: string | null = null;
  try {
    const image = await ImageManipulator.manipulate(uri).resize({ width: 1280 }).renderAsync();
    const saved = await image.saveAsync({ format: SaveFormat.JPEG, compress: 0.6, base64: true });
    savedUri = saved.uri;
    if (!saved.base64) throw new Error(text('capture.photoFailed'));
    return `data:image/jpeg;base64,${saved.base64}`;
  } finally {
    discardFiles(uri, savedUri);
  }
}
