import type { ReactNode } from 'react';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import Approve from '@/app/attendance/approve';
import Verify from '@/app/attendance/verify';
import { HR_API, isException } from '@/lib/attendance';
import { ThemeProvider } from '@/theme';

import { type Answer, fakeErp } from './fake-erp';

const entry = (name: string, extra: Record<string, unknown> = {}) => ({
  name, employee: `EMP-${name}`, employee_name: `Worker ${name}`, attendance_date: '2026-11-23', shift: 'S1 Day',
  attendance_status: 'Present', entry_type: 'Team', captured_offline: 0, check_in_time: '2026-11-23 08:10:00',
  accuracy_m: 9.6, can_review: true, ...extra,
});
const list = [entry('A'), entry('B', { captured_offline: 1 }), entry('C', { can_review: false }), entry('D', { attendance_status: 'Absent' })];
let mockErp = fakeErp({});
let mockDown = false; // no connection: every call fails as fetch does offline
const mockApiRef = {
  current: async (...a: Parameters<ReturnType<typeof fakeErp>['api']>) => {
    if (mockDown) throw new TypeError('Network request failed');
    return mockErp.api(...a);
  },
};
const serve = (review?: Answer) => {
  mockErp = fakeErp({
    [`${HR_API}.approvals`]: { body: { message: list } },
    [`${HR_API}.entry`]: { body: { message: { name: 'A', photo: '/private/files/field-A-1.jpg', remarks: 'On time' } } },
    [`${HR_API}.review_many`]:
      review ?? ((args) => ({ body: { message: (args.names as string[]).map((n) => ({ name: n, ok: true, state: 'Approved' })) } })),
  });
  return mockErp.calls;
};
jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useApiRef: () => mockApiRef }));
let mockConfirmed = true;
jest.mock('@/auth/confirm', () => ({ confirmIdentity: async () => mockConfirmed }));
jest.mock('expo-screen-capture', () => ({
  usePreventScreenCapture: () => {},
  enableAppSwitcherProtectionAsync: async () => {},
  disableAppSwitcherProtectionAsync: async () => {},
}));
jest.mock('@/components/private-image', () => {
  const { createElement } = jest.requireActual('react');
  const { Text } = jest.requireActual('react-native');
  return { PrivateImage: ({ path }: { path: string }) => createElement(Text, null, `photo ${path}`) };
});

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const open = () => renderRouter({ 'attendance/approve': Approve }, { initialUrl: '/attendance/approve?site=S1', wrapper });
const reviewed = () => mockErp.calls.find((c) => c.method === `${HR_API}.review_many`);

describe('PM approval', () => {
  beforeEach(() => {
    mockConfirmed = true;
    mockDown = false;
  });

  it('offline: the saved list can be read, but approving waits for a connection', async () => {
    serve();
    const first = await open();
    await screen.findByText('Worker A'); // online once: the list is saved
    await first.unmount();
    mockDown = true;
    await open();
    expect(await screen.findByText(/^Offline · data from \d\d:\d\d/)).toBeOnTheScreen();
    expect(screen.getByText('Worker A')).toBeOnTheScreen();
    expect(screen.getByText('Approving needs internet. You can look at the list now and approve when the signal is back.')).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Select all 3'));
    await fireEvent.press(screen.getByText('Approve 3'));
    expect(reviewed()).toBeUndefined();
  });

  it('lists what waits, marks offline captures and what this person may not review', async () => {
    serve();
    await open();
    expect(await screen.findByText('Worker A')).toBeOnTheScreen();
    expect(screen.getByText("Captured offline: the time comes from the phone's corrected clock.")).toBeOnTheScreen();
    expect(screen.getByText('You captured this, or it is your own attendance: another approver must review it.')).toBeOnTheScreen();
    expect(screen.getAllByText('Present · Marked by supervisor · at 08:10 · GPS ±10 m · 23-11-2026')).toHaveLength(3);
    // selection is a real checkbox (icon + state), not a text symbol
    expect(screen.getAllByRole('checkbox').map((c) => c.props.accessibilityState)).toEqual([
      { checked: false, disabled: false }, { checked: false, disabled: false }, { checked: false, disabled: true }, { checked: false, disabled: false },
    ]);
  });

  it('"select all" takes only what this person may review; one Face ID approves the selection', async () => {
    serve();
    await open();
    await fireEvent.press(await screen.findByText('Select all 3'));
    await fireEvent.press(screen.getByText('Approve 3'));
    expect(await screen.findByText('3 approved. HR attendance is recorded.')).toBeOnTheScreen();
    expect(reviewed()).toEqual({ method: `${HR_API}.review_many`, args: { names: ['A', 'B', 'D'], decision: 'Approve', remarks: '' }, post: true });
  });

  it('exceptions only: offline and absent entries', async () => {
    serve();
    await open();
    await fireEvent.press(await screen.findByText('Exceptions only (offline or absent)'));
    expect(screen.queryByText('Worker A')).toBeNull();
    expect(screen.getByText('Worker B')).toBeOnTheScreen();
    expect(screen.getByText('Worker D')).toBeOnTheScreen();
    expect([list[0], list[1], list[3]].map(isException)).toEqual([false, true, true]);
  });

  it('nothing is sent without Face ID, and a return needs a reason', async () => {
    serve();
    mockConfirmed = false;
    await open();
    await fireEvent.press(await screen.findByText('Worker A'));
    await fireEvent.press(screen.getByText('Approve 1'));
    expect(await screen.findByText('Not confirmed. Nothing was changed.')).toBeOnTheScreen();
    mockConfirmed = true;
    await fireEvent.press(screen.getByText('Return 1 for correction'));
    expect(screen.getByText('Write what needs correcting before returning.')).toBeOnTheScreen();
    expect(reviewed()).toBeUndefined();
    await fireEvent.changeText(screen.getByLabelText('Remarks (required to return)'), 'Photo is blurred');
    await fireEvent.press(screen.getByText('Return 1 for correction'));
    await screen.findByText(/returned to the supervisor/);
    expect(reviewed()!.args).toEqual({ names: ['A'], decision: 'Return', remarks: 'Photo is blurred' });
  });

  it('says per entry what was not done', async () => {
    serve({ body: { message: [{ name: 'A', ok: true, state: 'Approved' }, { name: 'B', ok: false, error: 'Self approval is not allowed' }] } });
    await open();
    await fireEvent.press(await screen.findByText('Worker A'));
    await fireEvent.press(screen.getByText('Worker B'));
    await fireEvent.press(screen.getByText('Approve 2'));
    expect(await screen.findByText('1 done. Not done: Worker B: Self approval is not allowed')).toBeOnTheScreen();
  });

  it("shows an entry's photo and remarks on request", async () => {
    serve();
    await open();
    await fireEvent.press((await screen.findAllByText('Show photo and remarks'))[0]);
    expect(await screen.findByText('photo /private/files/field-A-1.jpg')).toBeOnTheScreen();
    expect(screen.getByText('On time')).toBeOnTheScreen();
  });
});

describe('engineer check (Pending Verification, before the PM)', () => {
  const openVerify = () => renderRouter({ 'attendance/verify': Verify }, { initialUrl: '/attendance/verify?site=S1', wrapper });
  const toCheck = [
    { name: 'V1', employee_name: 'Worker V1', attendance_date: '2026-11-24', shift: 'S1 Day', attendance_status: 'Present' },
    { name: 'V2', employee_name: 'Worker V2', attendance_date: '2026-11-24', shift: 'S1 Day', attendance_status: 'Absent' },
  ];
  const serveChecks = (verify?: (args: Record<string, unknown>) => Answer) => {
    mockErp = fakeErp({
      [`${HR_API}.verifications`]: { body: { message: toCheck } },
      [`${HR_API}.verify`]: verify ?? ((args) => ({ body: { message: { name: args.name, state: args.decision === 'Verify' ? 'Verified' : 'Returned' } } })),
    });
    return mockErp.calls;
  };
  beforeEach(() => {
    mockConfirmed = true;
    mockDown = false;
  });

  it('lists what the supervisors marked; one Face ID verifies the selection, one call per entry', async () => {
    const calls = serveChecks();
    await openVerify();
    expect(await screen.findByText('Worker V1')).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Select all 2'));
    await fireEvent.press(screen.getByText('Verify 2'));
    expect(await screen.findByText('2 verified. They go to the project manager for approval.')).toBeOnTheScreen();
    expect(calls.filter((c) => c.method === `${HR_API}.verify`).map((c) => c.args)).toEqual([
      { name: 'V1', decision: 'Verify', remarks: '' },
      { name: 'V2', decision: 'Verify', remarks: '' },
    ]);
    expect(calls.some((c) => c.method === `${HR_API}.review_many`)).toBe(false);
  });

  it('returning needs a reason; a refusal for one entry is shown, the others go through', async () => {
    const calls = serveChecks((args) =>
      args.name === 'V2'
        ? { status: 403, body: { _server_messages: JSON.stringify([JSON.stringify({ message: 'Only the assigned engineer can verify this record.' })]) } }
        : { body: { message: { name: args.name, state: 'Returned' } } },
    );
    await openVerify();
    await fireEvent.press(await screen.findByText('Select all 2'));
    await fireEvent.press(screen.getByText('Return 2 for correction'));
    expect(calls.some((c) => c.method === `${HR_API}.verify`)).toBe(false);
    await fireEvent.changeText(screen.getByLabelText('Remarks (required to return)'), 'Photo unclear');
    await fireEvent.press(screen.getByText('Return 2 for correction'));
    expect(await screen.findByText(/1 done\. Not done: Worker V2: Only the assigned engineer can verify this record\./)).toBeOnTheScreen();
  });
});
