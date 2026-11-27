import { OfflineError, ServerError } from '@/lib/erp';
import { MAX_AGE_MS, type QueueItem, createQueue, memoryStore } from '@/lib/queue';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));

/** A queue with a fake clock and a fake sender that answers per item ID. */
function setup(answer: (item: QueueItem) => unknown = () => ({})) {
  let clock = 1_000_000;
  const sent: string[] = [];
  const store = memoryStore();
  const queue = createQueue(
    store,
    async (item) => {
      sent.push(item.id);
      const result = answer(item);
      if (result instanceof Error) throw result;
      return result;
    },
    () => clock,
  );
  const add = async (id: string) => {
    await queue.add('app.api.check_in', { request_id: id }, id);
    clock += 1000;
  };
  return { queue, sent, add, tick: (ms: number) => (clock += ms) };
}

describe('offline queue', () => {
  it('sends in the order items were made and removes what was sent', async () => {
    const { queue, sent, add } = setup();
    await add('a');
    await add('b');
    await add('c');
    await expect(queue.flush()).resolves.toEqual({ sent: 3, failed: 0, stopped: false });
    expect(sent).toEqual(['a', 'b', 'c']);
    expect(await queue.waiting()).toEqual([]);
  });

  it('stops at a lost connection, keeps the order and sends the same item (same client ID) next time', async () => {
    let online = false;
    const { queue, sent, add } = setup(() => (online ? {} : new OfflineError('offline')));
    await add('a');
    await add('b');
    await queue.flush();
    expect(sent).toEqual(['a']);
    expect((await queue.waiting()).map((i) => [i.id, i.attempts, i.args.request_id])).toEqual([
      ['a', 1, 'a'],
      ['b', 0, 'b'],
    ]);
    online = true;
    await queue.flush();
    expect(sent).toEqual(['a', 'a', 'b']);
    expect(await queue.waiting()).toEqual([]);
  });

  it("keeps a refused item with ERPNext's reason and goes on with the rest", async () => {
    const { queue, add } = setup((i) => (i.id === 'a' ? new ServerError('You are outside the site fence.', 417) : {}));
    await add('a');
    await add('b');
    await expect(queue.flush()).resolves.toEqual({ sent: 1, failed: 1, stopped: false });
    expect((await queue.failed()).map((i) => [i.id, i.error])).toEqual([['a', 'You are outside the site fence.']]);
    await queue.dismiss('a');
    expect(await queue.failed()).toEqual([]);
  });

  it('keeps waiting on server trouble or anything unexpected', async () => {
    for (const problem of [new ServerError('busy', 503), new Error('signed out')]) {
      const { queue, add } = setup(() => problem);
      await add('a');
      await expect(queue.flush()).resolves.toEqual({ sent: 0, failed: 0, stopped: true });
      expect((await queue.waiting()).map((i) => i.state)).toEqual(['waiting']);
    }
  });

  it('removes items older than a day and says so', async () => {
    const { queue, sent, add, tick } = setup();
    await add('old');
    tick(MAX_AGE_MS);
    await add('new');
    const dropped = await queue.purge();
    expect(dropped.map((i) => i.id)).toEqual(['old']);
    expect(dropped[0].error).toContain('Not sent within a day');
    await queue.flush();
    expect(sent).toEqual(['new']);
  });

  it('runs one send at a time', async () => {
    const { queue, sent, add } = setup();
    await add('a');
    await Promise.all([queue.flush(), queue.flush()]);
    expect(sent).toEqual(['a']);
  });

  it('removes everything at sign-out', async () => {
    const { queue, add } = setup(() => new OfflineError('offline'));
    await add('a');
    await queue.clear();
    expect(await queue.waiting()).toEqual([]);
  });
});
