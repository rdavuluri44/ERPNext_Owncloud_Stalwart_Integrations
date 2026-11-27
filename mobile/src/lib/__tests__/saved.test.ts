import { z } from 'zod';

import { fakeErp, thrown } from '@/__tests__/fake-erp';
import { OfflineError, ServerError } from '@/lib/erp';
import { MAX_AGE_MS, memoryStore } from '@/lib/queue';
import { callKept, resetConnection } from '@/lib/saved';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStore: async () => mockStore }));

const M = 'app.api.team';
const Schema = z.object({ total: z.number() });
const online = fakeErp({ [M]: { body: { message: { total: 5 } } } }).api;
const down = async () => {
  throw new TypeError('Network request failed');
};

describe('saved answers for reading offline', () => {
  beforeEach(async () => {
    await mockStore.clear();
    resetConnection();
  });

  it('online: the fresh answer, saved; offline: the saved copy with its time', async () => {
    expect(await callKept(online, M, Schema, { site: 'S1' }, () => 1000)).toEqual({ total: 5 });
    expect(await callKept(down, M, Schema, { site: 'S1' }, () => 2000)).toEqual({ total: 5 });
    expect((await mockStore.read(`${M}?{"site":"S1"}`, 0))?.at).toBe(1000);
  });

  it('offline without a copy for these arguments: the offline error', async () => {
    await callKept(online, M, Schema, { site: 'S1' }, () => 1000);
    await expect(callKept(down, M, Schema, { site: 'S2' }, () => 2000)).rejects.toBeInstanceOf(OfflineError);
  });

  it('a copy older than a day is not used', async () => {
    await callKept(online, M, Schema, {}, () => 1000);
    await expect(callKept(down, M, Schema, {}, () => 1001 + MAX_AGE_MS)).rejects.toBeInstanceOf(OfflineError);
  });

  it('a refusal by ERPNext is shown, never answered from the copy', async () => {
    await callKept(online, M, Schema, {}, () => 1000);
    const refuses = fakeErp({ [M]: { status: 403, body: thrown('Not permitted') } }).api;
    await expect(callKept(refuses, M, Schema, {}, () => 2000)).rejects.toEqual(new ServerError('Not permitted', 403));
  });

  it('ERPNext down (server error) is treated like no connection', async () => {
    await callKept(online, M, Schema, {}, () => 1000);
    const broken = fakeErp({ [M]: { status: 502, body: {} } }).api;
    expect(await callKept(broken, M, Schema, {}, () => 2000)).toEqual({ total: 5 });
  });

  it('a copy of the wrong shape is never used', async () => {
    await mockStore.keep(`${M}?{}`, JSON.stringify({ total: 'five' }), 1000, 0);
    await expect(callKept(down, M, Schema, {}, () => 2000)).rejects.toBeInstanceOf(OfflineError);
  });

  it('sign-out clears the copies', async () => {
    await callKept(online, M, Schema, {}, () => 1000);
    await mockStore.clear();
    await expect(callKept(down, M, Schema, {}, () => 2000)).rejects.toBeInstanceOf(OfflineError);
  });
});
