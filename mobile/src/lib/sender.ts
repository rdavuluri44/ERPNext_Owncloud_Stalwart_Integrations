// Sends a capture now, or keeps it in the encrypted offline queue when there is no connection (build guide
// section 8). The client ID inside the request (request_id / capture_id) makes every retry return the same
// record on the server. A refusal by ERPNext is never queued: the person sees it at once.
import { z } from 'zod';

import { offlineFields } from '@/lib/capture';
import { type Api, OfflineError, callErp } from '@/lib/erp';
import { offlineStore } from '@/lib/offline-store';
import { createQueue } from '@/lib/queue';

let api: Api | null = null;
let queue: ReturnType<typeof createQueue> | null = null;

async function getQueue(current: Api) {
  api = current;
  if (!queue) {
    const store = await offlineStore();
    queue = createQueue(store, (item) => {
      if (!api) throw new OfflineError('not signed in');
      return callErp(api, item.method, z.unknown(), item.args, { post: true });
    });
  }
  return queue;
}

export type Sent<T> = { sent: true; result: T } | { queued: true };

/**
 * POST a capture (`self_check_in`, `self_check_out`, `save_capture`: each takes one `payload`) now; without a
 * connection, keep it with the offline time fields inside the payload (the phone's clock at `capturedAt` and
 * the measured difference to the server) under the client ID `id`.
 */
export async function sendOrQueue<S extends z.ZodType>(
  current: Api,
  method: string,
  schema: S,
  payload: Record<string, unknown>,
  id: string,
  capturedAt: Date,
): Promise<Sent<z.infer<S>>> {
  try {
    return { sent: true, result: await callErp(current, method, schema, { payload }, { post: true }) };
  } catch (e) {
    if (!(e instanceof OfflineError)) throw e;
    // ponytail: if the lost request did reach the server, a supervisor's retry with these extra offline
    // fields is refused as "changed"; the draft is then already there (seen in the team list).
    await (await getQueue(current)).add(method, { payload: { ...payload, ...(await offlineFields(capturedAt)) } }, id);
    return { queued: true };
  }
}

/** Send what waits, oldest first (app opened or brought to the front, Today opened, after a capture). */
export async function flushQueue(current: Api) {
  return (await getQueue(current)).flush();
}
