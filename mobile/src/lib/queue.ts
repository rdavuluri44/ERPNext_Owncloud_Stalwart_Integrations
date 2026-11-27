// Offline queue (build guide sections 7 and 8). Anything created without a connection waits here and is
// sent in order when the phone is back online. The client ID the caller puts in the request (for example
// `request_id`) is also the item's ID, so a retry after a lost answer returns the same record on the server.
import * as Crypto from 'expo-crypto';

import { t } from '@/i18n';
import { ServerError } from '@/lib/erp';

export type QueueItem = {
  /** The client ID: unique per record, sent to the server inside `args`. */
  id: string;
  /** Whitelisted ERPNext method, for example `erpnext_drive_integrations.custom_hr.api.self_check_in`. */
  method: string;
  args: Record<string, unknown>;
  createdAt: number;
  attempts: number;
  /** waiting: will be sent; failed: the server refused it (the person must look at `error`). */
  state: 'waiting' | 'failed';
  error?: string;
};

/**
 * Where items live: the encrypted database on a development build, memory in Expo Go and tests. The same
 * store keeps the last good server answers for reading offline (lib/saved.ts).
 */
export interface QueueStore {
  /** True only for the SQLCipher database whose encryption was confirmed. */
  encrypted?: boolean;
  all(): Promise<QueueItem[]>;
  put(item: QueueItem): Promise<void>;
  remove(id: string): Promise<void>;
  /** A saved answer, if saved at or after `notBefore` (milliseconds). */
  read(key: string, notBefore: number): Promise<{ at: number; body: string } | null>;
  /** Save an answer at `at`; answers saved before `notBefore` are deleted. */
  keep(key: string, body: string, at: number, notBefore: number): Promise<void>;
  /** Delete queued items and saved answers older than `notBefore` (owner: data stays at most a day). */
  purge(notBefore: number): Promise<void>;
  /** Everything: queued items and saved answers (sign-out). */
  clear(): Promise<void>;
}

/** Owner: data may stay on the phone at most one day; the server refuses older offline captures anyway. */
export const MAX_AGE_MS = 24 * 60 * 60 * 1000;

export const newClientId = () => Crypto.randomUUID();

export function memoryStore(): QueueStore {
  const items = new Map<string, QueueItem>();
  const saved = new Map<string, { at: number; body: string }>();
  return {
    all: async () => [...items.values()].map((i) => ({ ...i, args: { ...i.args } })),
    put: async (item) => void items.set(item.id, { ...item, args: { ...item.args } }),
    remove: async (id) => void items.delete(id),
    read: async (key, notBefore) => {
      const s = saved.get(key);
      return s && s.at >= notBefore ? s : null;
    },
    keep: async (key, body, at, notBefore) => {
      for (const [k, s] of saved) if (s.at < notBefore) saved.delete(k);
      saved.set(key, { at, body });
    },
    purge: async (notBefore) => {
      for (const [k, i] of items) if (i.createdAt < notBefore) items.delete(k);
      for (const [k, s] of saved) if (s.at < notBefore) saved.delete(k);
    },
    clear: async () => {
      items.clear();
      saved.clear();
    },
  };
}

type Send = (item: QueueItem) => Promise<unknown>;

export function createQueue(store: QueueStore, send: Send, now: () => number = Date.now) {
  let flushing: Promise<{ sent: number; failed: number; stopped: boolean }> | null = null;

  const ordered = async () => (await store.all()).sort((a, b) => a.createdAt - b.createdAt);

  /** Remove items older than a day; returns them so the person can be told what was dropped. */
  const purge = async () => {
    const old = (await store.all()).filter((i) => now() - i.createdAt > MAX_AGE_MS);
    for (const item of old) await store.remove(item.id);
    return old.map((i) => ({ ...i, error: t('queue.expired') }));
  };

  const flushOnce = async () => {
    await purge();
    let sent = 0;
    let failed = 0;
    let stopped = false;
    for (const item of await ordered()) {
      if (item.state !== 'waiting') continue;
      try {
        await send(item);
        await store.remove(item.id);
        sent++;
      } catch (e) {
        if (e instanceof ServerError && !e.retry) {
          // ERPNext refused this item (for example outside the site fence): keep it for the person to see.
          await store.put({ ...item, attempts: item.attempts + 1, state: 'failed', error: e.message });
          failed++;
          continue;
        }
        // Offline, a server or rate problem, or anything unexpected (for example signed out): the item keeps
        // waiting, and nothing after it is sent before it.
        await store.put({ ...item, attempts: item.attempts + 1 });
        stopped = true; // no connection (or server trouble): the rest waits too
        break;
      }
    }
    return { sent, failed, stopped };
  };

  return {
    /** Keep a request until it is sent. `id` must be the client ID inside `args`. */
    async add(method: string, args: Record<string, unknown>, id: string) {
      const item: QueueItem = { id, method, args, createdAt: now(), attempts: 0, state: 'waiting' };
      await store.put(item);
      return item;
    },
    /** Send waiting items, oldest first; one run at a time. */
    flush() {
      flushing ??= flushOnce().finally(() => {
        flushing = null;
      });
      return flushing;
    },
    purge,
    async waiting() {
      return (await ordered()).filter((i) => i.state === 'waiting');
    },
    async failed() {
      return (await ordered()).filter((i) => i.state === 'failed');
    },
    /** A refused item the person has read and dismissed. */
    dismiss: (id: string) => store.remove(id),
    /** Sign-out and remote wipe: nothing stays on the phone. */
    clear: () => store.clear(),
  };
}
