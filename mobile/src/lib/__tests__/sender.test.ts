import { z } from 'zod';

import { fakeErp, thrown } from '@/__tests__/fake-erp';
import { OfflineError, ServerError } from '@/lib/erp';
import { memoryStore } from '@/lib/queue';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStore: async () => mockStore }));
jest.mock('@/lib/capture', () => ({
  offlineFields: async (d: Date) => ({ offline: 1, device_captured_at: `phone ${d.getHours()}:00`, clock_offset_s: 120 }),
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { flushQueue, sendOrQueue } = require('@/lib/sender') as typeof import('@/lib/sender');

const METHOD = 'erpnext_drive_integrations.custom_hr.api.self_check_in';
const at = new Date(2026, 10, 23, 8, 0, 0);
const payload = { site: 'S1', shift: 'Day', request_id: 'r'.repeat(16) };

describe('send or queue', () => {
  beforeEach(() => mockStore.clear());

  it('online: sends the payload as JSON and returns the checked answer', async () => {
    const { api, calls } = fakeErp({ [METHOD]: { body: { message: { name: 'E1' } } } });
    expect(await sendOrQueue(api, METHOD, z.object({ name: z.string() }), payload, 'id1', at)).toEqual({ sent: true, result: { name: 'E1' } });
    expect(calls[0]).toEqual({ method: METHOD, args: { payload }, post: true });
    expect(await mockStore.all()).toEqual([]);
  });

  it('offline: keeps it encrypted with the offline fields inside the payload, under its client ID', async () => {
    const offline: Parameters<typeof sendOrQueue>[0] = async () => {
      throw new TypeError('Network request failed');
    };
    expect(await sendOrQueue(offline, METHOD, z.unknown(), payload, 'id1', at)).toEqual({ queued: true });
    const [item] = await mockStore.all();
    expect(item.id).toBe('id1');
    expect(item.args).toEqual({ payload: { ...payload, offline: 1, device_captured_at: 'phone 8:00', clock_offset_s: 120 } });
  });

  it('a refusal by ERPNext is shown, never queued', async () => {
    const { api } = fakeErp({ [METHOD]: { status: 417, body: thrown('You are outside this site’s permitted attendance area.') } });
    await expect(sendOrQueue(api, METHOD, z.unknown(), payload, 'id1', at)).rejects.toBeInstanceOf(ServerError);
    expect(await mockStore.all()).toEqual([]);
  });

  it('the queue sends the kept item later, unchanged', async () => {
    const offline: Parameters<typeof sendOrQueue>[0] = async () => {
      throw new OfflineError('offline');
    };
    await sendOrQueue(offline, METHOD, z.unknown(), payload, 'id1', at).catch(() => {});
    // the plain OfflineError above is thrown by `api` itself: callErp turns any api failure into OfflineError
    const { api, calls } = fakeErp({ [METHOD]: { body: { message: { name: 'E1' } } } });
    await flushQueue(api);
    expect(calls.map((c) => c.args)).toEqual([{ payload: { ...payload, offline: 1, device_captured_at: 'phone 8:00', clock_offset_s: 120 } }]);
    expect(await mockStore.all()).toEqual([]);
  });
});
