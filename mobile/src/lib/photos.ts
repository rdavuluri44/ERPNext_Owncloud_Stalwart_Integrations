// Site photos (P74, owner 24 November 2026): saved in the project's Drive space through ERPNext only
// (erpnext_drive_integrations.drive_store.api). The phone keeps no photo files: a photo waits only in the
// encrypted offline queue until it is sent; previews are kept in memory while the app is open.
import { z } from 'zod';

import { type Api } from '@/lib/erp';
import { callKept } from '@/lib/saved';

export const PHOTO_API = 'erpnext_drive_integrations.drive_store.api';
export const KINDS = ['Progress', 'Hindrance', 'Incident', 'Other'] as const;
export type Kind = (typeof KINDS)[number];

export const Uploaded = z.object({ name: z.string(), path: z.string() });

export const PhotoList = z.array(
  z.object({
    name: z.string(),
    project: z.string(),
    site: z.string(),
    kind: z.string(),
    taken_at: z.string(),
    taken_by: z.string(),
    from_gallery: z.coerce.number().nullish(),
    captured_offline: z.coerce.number().nullish(),
    latitude: z.number().nullish(),
    longitude: z.number().nullish(),
    accuracy_m: z.number().nullish(),
    remarks: z.string().nullish(),
  }),
);
export type PhotoT = z.infer<typeof PhotoList>[number];
export const PAGE = 30;

/** One page of the photos the person may see (server decides), newest first. The list is kept for offline. */
export function listPhotos(api: Api, filters: { site?: string; kind?: string; start?: number }) {
  const args: Record<string, unknown> = { start: filters.start ?? 0 };
  if (filters.site) args.site = filters.site;
  if (filters.kind) args.kind = filters.kind;
  return callKept(api, `${PHOTO_API}.photos`, PhotoList, args);
}

// ---- previews in memory only (owner: a few photos at a time; Claude: about the last 100) ----
const MAX_PREVIEWS = 100;
const previews = new Map<string, string>();

/** Remember a preview; the oldest is forgotten past 100. */
export function keepPreview(key: string, dataUrl: string) {
  previews.delete(key);
  previews.set(key, dataUrl);
  while (previews.size > MAX_PREVIEWS) previews.delete(previews.keys().next().value as string);
}
export const cachedPreview = (key: string) => previews.get(key) ?? null;
/** Sign-out: no photo stays in memory. */
export const clearPreviews = () => previews.clear();

/** A photo (preview or full) as a data URL, fetched as the signed-in person (ERPNext checks access). */
export async function photoImage(api: Api, name: string, size: 'preview' | 'full'): Promise<string> {
  const key = `${name}:${size}`;
  const known = previews.get(key);
  if (known) return known;
  const res = await api(`/api/method/${PHOTO_API}.photo?${new URLSearchParams({ name, size })}`);
  if (!res.ok) throw new Error(String(res.status));
  const dataUrl = await asDataUrl(await res.blob());
  if (size === 'preview') keepPreview(key, dataUrl); // full photos are never kept
  return dataUrl;
}

// ---- project files (P74 S3): a project's Drive space, read through ERPNext ----
export const FileList = z.array(
  z.object({ name: z.string(), path: z.string(), folder: z.boolean(), size: z.number(), modified: z.string().nullish(), type: z.string().nullish() }),
);
export type FileT = z.infer<typeof FileList>[number];
export const isImage = (path: string) => /\.(jpe?g|png|webp|gif)$/i.test(path);

/** One folder of a project's Drive space (kept for offline like other lists). */
export const listFiles = (api: Api, project: string, path: string) => callKept(api, `${PHOTO_API}.files`, FileList, { project, path });

/** An image from a project's space as a data URL; previews are kept in memory like photo previews. */
export async function fileImage(api: Api, project: string, path: string, size: 'preview' | 'full'): Promise<string> {
  const key = `file:${project}:${path}:${size}`;
  const known = previews.get(key);
  if (known) return known;
  const res = await api(`/api/method/${PHOTO_API}.file?${new URLSearchParams({ project, path, size })}`);
  if (!res.ok) throw new Error(String(res.status));
  const dataUrl = await asDataUrl(await res.blob());
  if (size === 'preview') keepPreview(key, dataUrl);
  return dataUrl;
}

function asDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('unreadable image'));
    reader.readAsDataURL(blob);
  });
}
