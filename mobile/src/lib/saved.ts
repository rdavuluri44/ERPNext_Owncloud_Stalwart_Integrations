// Reading offline (build guide sections 5 and 8; owner, 23 November 2026). The last good answer of each read
// that field work needs (sites and shifts, team lists, own attendance, approval lists, the Inbox) is kept in
// the encrypted offline store, at most one day, and deleted at sign-out. Without a connection the screens show
// that copy, with the time it was saved. Payslips and leave are never kept (owner). The copy is for reading:
// approving needs a connection; captures go through the offline queue (lib/sender.ts).
import { useSyncExternalStore } from 'react';
import type { z } from 'zod';

import { type Api, OfflineError, ServerError, callErp } from '@/lib/erp';
import { offlineStore } from '@/lib/offline-store';
import { MAX_AGE_MS } from '@/lib/queue';

/** offline: the last read could not reach ERPNext. copyFrom: the oldest saved copy on screen (milliseconds). */
export type Connection = { offline: boolean; copyFrom: number | null };

let state: Connection = { offline: false, copyFrom: null };
const listeners = new Set<() => void>();
function set(next: Connection) {
  if (next.offline === state.offline && next.copyFrom === state.copyFrom) return;
  state = next;
  listeners.forEach((l) => l());
}

/** Sign-out: forget the last person's offline state. */
export const resetConnection = () => set({ offline: false, copyFrom: null });

/**
 * `callErp` for a read (GET) whose answer is kept for offline use. Online: the fresh answer, saved. No
 * connection (or ERPNext down): the saved copy if there is one from the last day (checked against `schema`
 * again), otherwise the error. A refusal by ERPNext is never answered from the copy.
 */
export async function callKept<S extends z.ZodType>(
  api: Api,
  method: string,
  schema: S,
  args: Record<string, unknown> = {},
  now: () => number = Date.now,
): Promise<z.infer<S>> {
  const key = `${method}?${JSON.stringify(args)}`;
  const store = await offlineStore();
  try {
    const data = await callErp(api, method, schema, args);
    await store.keep(key, JSON.stringify(data), now(), now() - MAX_AGE_MS);
    set({ offline: false, copyFrom: null });
    return data;
  } catch (e) {
    if (!(e instanceof OfflineError || (e instanceof ServerError && e.retry))) throw e;
    const copy = await store.read(key, now() - MAX_AGE_MS);
    const checked = copy ? schema.safeParse(JSON.parse(copy.body)) : null;
    if (!copy || !checked?.success) {
      set({ offline: true, copyFrom: state.copyFrom });
      throw e;
    }
    set({ offline: true, copyFrom: Math.min(state.copyFrom ?? copy.at, copy.at) });
    return checked.data;
  }
}

const subscribe = (l: () => void) => {
  listeners.add(l);
  return () => listeners.delete(l);
};

export function useConnection(): Connection {
  return useSyncExternalStore(subscribe, () => state);
}
