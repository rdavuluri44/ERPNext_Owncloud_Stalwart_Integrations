import type { ComponentProps, ReactNode } from 'react';
import { Text } from 'react-native';
import { act, fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import Inbox from '@/app/(app)/inbox';
import DocScreen from '@/app/doc/[doctype]/[name]';
import { ACTIONS_METHOD, LOGS_METHOD, MARK_READ_METHOD, clearInbox } from '@/lib/inbox';
import { APPLY_METHOD, TRANSITIONS_METHOD } from '@/components/workflow-actions';
import { ThemeProvider } from '@/theme';

import { type Answer, fakeErp, thrown } from './fake-erp';

const mockErp: { current: ReturnType<typeof fakeErp> } = { current: fakeErp({}) };
const mockApiRef = { current: (...a: Parameters<ReturnType<typeof fakeErp>['api']>) => mockErp.current.api(...a) };
jest.mock('@/auth/session', () => ({
  SignedOutError: class SignedOutError extends Error {},
  useAuth: () => ({ api: mockApiRef.current }),
  useApiRef: () => mockApiRef,
}));
let mockConfirmed = true;
const mockConfirm = jest.fn(async (_reason: string) => mockConfirmed);
jest.mock('@/auth/confirm', () => ({ confirmIdentity: (reason: string) => mockConfirm(reason) }));
jest.mock('@/components/doc-view', () => ({ DocView: () => null }));
const mockWorkflowPresses = new Map<string, () => void>();
jest.mock('@/components/ui', () => {
  const ui = jest.requireActual<typeof import('@/components/ui')>('@/components/ui');
  return {
    ...ui,
    Button: (props: ComponentProps<typeof ui.Button>) => {
      mockWorkflowPresses.set(props.label, props.onPress);
      return <ui.Button {...props} />;
    },
  };
});

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const action = { name: 'WA-1', reference_doctype: 'Purchase Order', reference_name: 'PO-0001', workflow_state: 'Pending', creation: '2026-11-23 10:00:00' };
const note = { name: 'NL-1', subject: '<b>PO-0001</b> needs approval', document_type: 'Purchase Order', document_name: 'PO-0001', read: 0, creation: '2026-11-23 10:01:00' };

function serve(apply: Answer = { body: { message: { name: 'PO-0001' } } }) {
  mockErp.current = fakeErp({
    [ACTIONS_METHOD]: { body: { message: [action] } },
    [LOGS_METHOD]: { body: { message: { notification_logs: [note], user_info: {} } } },
    [MARK_READ_METHOD]: { body: { message: null } },
    [TRANSITIONS_METHOD]: { body: { message: [{ action: 'Approve', next_state: 'Approved' }, { action: 'Reject', next_state: 'Rejected' }] } },
    [APPLY_METHOD]: apply,
  });
  return mockErp.current.calls;
}
const app = { '(app)/inbox': Inbox, 'doc/[doctype]/[name]': DocScreen, index: () => <Text>home</Text> };
const openInbox = () => renderRouter(app, { initialUrl: '/inbox', wrapper });

describe('inbox screen', () => {
  beforeEach(() => {
    clearInbox();
    mockWorkflowPresses.clear();
    mockConfirmed = true;
    mockConfirm.mockReset().mockImplementation(async () => mockConfirmed);
  });

  it('lists what waits for the person and their notifications, unread marked in words', async () => {
    serve();
    await openInbox();
    expect(await screen.findByText('WAITING FOR YOU (1)')).toBeOnTheScreen();
    expect(screen.getByText('Purchase Order')).toBeOnTheScreen();
    expect(screen.getByText('PO-0001 needs approval')).toBeOnTheScreen();
    expect(screen.getByText('Unread · 23-11-2026 10:01')).toBeOnTheScreen();
  });

  it('opening a notification marks it read and opens its document', async () => {
    const calls = serve();
    const router = await openInbox();
    await fireEvent.press(await screen.findByText('PO-0001 needs approval'));
    expect(calls.some((c) => c.method === MARK_READ_METHOD && c.post && c.args.docname === 'NL-1')).toBe(true);
    expect(router.getPathname()).toBe('/doc/Purchase Order/PO-0001');
  });

  it("an approval opens with ERPNext's actions; Face ID first, then the action is applied", async () => {
    const calls = serve();
    await openInbox();
    await fireEvent.press(await screen.findByText('Purchase Order'));
    await fireEvent.press(await screen.findByText('Approve'));
    expect(mockConfirm).toHaveBeenCalledWith('Confirm Approve for PO-0001');
    expect(await screen.findByText('Approve: done. Now: Approved.')).toBeOnTheScreen();
    const applied = calls.find((c) => c.method === APPLY_METHOD)!;
    expect(applied.post).toBe(true);
    expect(applied.args).toEqual({ doc: { doctype: 'Purchase Order', name: 'PO-0001' }, action: 'Approve' });
  });

  it('ignores another action while identity confirmation is pending', async () => {
    const calls = serve();
    let confirm!: (value: boolean) => void;
    mockConfirm.mockImplementationOnce(() => new Promise<boolean>((resolve) => { confirm = resolve; }));
    await openInbox();
    await fireEvent.press(await screen.findByText('Purchase Order'));

    await screen.findByText('Approve');
    const approve = mockWorkflowPresses.get('Approve')!;
    const reject = mockWorkflowPresses.get('Reject')!;
    await act(async () => {
      approve();
      reject();
    });
    expect(mockConfirm).toHaveBeenCalledTimes(1);
    expect(calls.some((c) => c.method === APPLY_METHOD)).toBe(false);

    await act(async () => { confirm(true); });
    expect(await screen.findByText('Approve: done. Now: Approved.')).toBeOnTheScreen();
    expect(calls.filter((c) => c.method === APPLY_METHOD)).toHaveLength(1);
  });

  it('nothing is sent when Face ID is not confirmed', async () => {
    const calls = serve();
    mockConfirmed = false;
    await openInbox();
    await fireEvent.press(await screen.findByText('Purchase Order'));
    await fireEvent.press(await screen.findByText('Reject'));
    expect(await screen.findByText('Not confirmed. Nothing was changed.')).toBeOnTheScreen();
    expect(calls.some((c) => c.method === APPLY_METHOD)).toBe(false);
  });

  it("shows ERPNext's refusal as it gives it", async () => {
    serve({ status: 417, body: thrown('Self approval is not allowed') });
    await openInbox();
    await fireEvent.press(await screen.findByText('Purchase Order'));
    await fireEvent.press(await screen.findByText('Approve'));
    expect(await screen.findByText('Self approval is not allowed')).toBeOnTheScreen();
  });
});
