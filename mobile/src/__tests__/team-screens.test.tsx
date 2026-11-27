import type { ReactNode } from 'react';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import MarkWorker from '@/app/attendance/mark';
import TeamScreen from '@/app/attendance/team';
import { HR_API } from '@/lib/attendance';
import { memoryStore } from '@/lib/queue';
import { ThemeProvider } from '@/theme';

import { type Answer, fakeErp, thrown } from './fake-erp';

const shift = { name: 'S1 Day', start: '08:00', end: '20:00', label: 'Day' };
const boot = {
  server_now: '2026-11-23 08:00:00',
  sites: [{
    name: 'S1', label: 'Site 1', supervisor: true, approver: false, shifts: [shift], assets: [{ name: 'EXC-1', label: 'Excavator 1' }],
    supervisors: [{ user: 'sup-b@example.com', label: 'Supervisor B' }],
  }],
  check_in_sites: [],
};
const worker = (employee: string, state: string, extra: Record<string, unknown> = {}) => ({
  employee, employee_name: `Worker ${employee}`, designation: 'Helper', machine_required: 0, state, entry: null, revision: null,
  can_capture: true, can_edit: false, ...extra,
});
let mockErp = fakeErp({});
let mockDown = false; // no connection: every call fails as fetch does offline
const mockApiRef = {
  current: async (...a: Parameters<ReturnType<typeof fakeErp>['api']>) => {
    if (mockDown) throw new TypeError('Network request failed');
    return mockErp.api(...a);
  },
};
const serve = (over: Record<string, Answer> = {}) => {
  mockErp = fakeErp({
    [`${HR_API}.bootstrap`]: { body: { message: boot } },
    [`${HR_API}.team`]: {
      body: {
        message: {
          total: 3, missing: 2, attendance_date: '2026-11-23',
          workers: [worker('A', 'Not recorded'), worker('B', 'Draft', { entry: 'FAE-1', revision: 1, can_edit: true }), worker('C', 'Submitted', { can_capture: false, supervisor: 'sup-b@example.com' })],
        },
      },
    },
    [`${HR_API}.submit`]: { body: { message: { name: 'FAE-1', state: 'Submitted' } } },
    [`${HR_API}.save_capture`]: { body: { message: { name: 'FAE-2', state: 'Draft', revision: 1 } } },
    ...over,
  });
  return mockErp.calls;
};
jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useApiRef: () => mockApiRef }));
let mockConfirmed = true;
jest.mock('@/auth/confirm', () => ({ confirmIdentity: async () => mockConfirmed }));
jest.mock('@/lib/capture', () => ({
  ...jest.requireActual('@/lib/capture'),
  getFix: async () => ({ latitude: 17.385, longitude: 78.4867, accuracy_m: 9, gps_captured_at: '2026-11-23 08:05:00' }),
  rememberServerClock: async () => {},
  offlineFields: async () => ({ offline: 1, device_captured_at: '2026-11-23 08:05:00', clock_offset_s: 0 }),
}));
jest.mock('expo-image-manipulator', () => ({ ImageManipulator: {}, SaveFormat: { JPEG: 'jpeg' } }));
jest.mock('expo-location', () => ({}));
let mockIds = 0;
jest.mock('expo-crypto', () => ({ randomUUID: () => `id-0000-0000-0000-000${++mockIds}` }));
jest.mock('expo-screen-capture', () => ({
  usePreventScreenCapture: () => {},
  enableAppSwitcherProtectionAsync: async () => {},
  disableAppSwitcherProtectionAsync: async () => {},
}));
jest.mock('@/components/photo-taker', () => {
  const { createElement } = jest.requireActual('react');
  const { Pressable, Text } = jest.requireActual('react-native');
  return {
    PhotoTaker: ({ onPhoto }: { onPhoto: (d: string) => void }) =>
      createElement(Pressable, { onPress: () => onPhoto('data:image/jpeg;base64,BBBB') }, createElement(Text, null, 'Take photo')),
  };
});
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStore: async () => mockStore }));

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const app = { 'attendance/team': TeamScreen, 'attendance/mark': MarkWorker };
const openTeam = () => renderRouter(app, { initialUrl: '/attendance/team?site=S1&shift=S1%20Day', wrapper });
const markUrl = (q: string) => renderRouter(app, { initialUrl: `/attendance/mark?site=S1&shift=S1%20Day&employee=A&workerName=Worker%20A&${q}`, wrapper });
const saved = () => mockErp.calls.find((c) => c.method === `${HR_API}.save_capture`)?.args.payload as Record<string, unknown> | undefined;

describe('supervisor team', () => {
  beforeEach(async () => {
    mockConfirmed = true;
    mockDown = false;
    await mockStore.clear();
  });

  it('offline: the saved list, and a worker marked on this phone waits to be sent', async () => {
    serve();
    const first = await openTeam();
    await screen.findByText('1 of 3 marked for 23-11-2026'); // online once: the list is saved
    await first.unmount();
    mockDown = true;
    await mockStore.put({
      id: 'c1', method: `${HR_API}.save_capture`, args: { payload: { employee: 'A', site: 'S1', shift: 'S1 Day' } },
      createdAt: Date.now(), attempts: 0, state: 'waiting',
    });
    await openTeam();
    expect(await screen.findByText(/^Offline · data from \d\d:\d\d/)).toBeOnTheScreen();
    expect(screen.getByText('Marked, waiting to send')).toBeOnTheScreen();
    expect(screen.queryByText('Not recorded')).toBeNull();
    expect(screen.getByText('Draft')).toBeOnTheScreen();
  });

  it('lists the shift: counts, each state in words, and the drafts to submit', async () => {
    serve();
    await openTeam();
    expect(await screen.findByText('1 of 3 marked for 23-11-2026')).toBeOnTheScreen();
    expect(screen.getByText('Not recorded: tap to mark')).toBeOnTheScreen();
    expect(screen.getByText('Draft')).toBeOnTheScreen();
    expect(screen.getByText('Submit 1 for approval')).toBeOnTheScreen();
    // another supervisor's worker: seen, not markable, and the row says who marks them
    expect(screen.getByText('Helper · Supervisor: Supervisor B')).toBeOnTheScreen();
    expect(screen.getByText('Workers with another supervisor are marked by that supervisor.')).toBeOnTheScreen();
  });

  it('submits own drafts after Face ID, and not without it', async () => {
    const calls = serve();
    mockConfirmed = false;
    await openTeam();
    await fireEvent.press(await screen.findByText('Submit 1 for approval'));
    expect(calls.some((c) => c.method === `${HR_API}.submit`)).toBe(false);
    mockConfirmed = true;
    await fireEvent.press(screen.getByText('Submit 1 for approval'));
    expect(await screen.findByText('1 sent to the approvers.')).toBeOnTheScreen();
    expect(calls.find((c) => c.method === `${HR_API}.submit`)).toEqual({ method: `${HR_API}.submit`, args: { name: 'FAE-1' }, post: true });
  });

  it('opening a worker goes to marking with their details', async () => {
    serve();
    const router = await openTeam();
    await fireEvent.press(await screen.findByText('Worker A'));
    expect(router.getPathname()).toBe('/attendance/mark');
    expect(router.getSearchParams()).toMatchObject({ employee: 'A', machine: '0', entry: '', revision: '0' });
  });
});

describe('marking a worker', () => {
  beforeEach(() => mockStore.clear());

  it('Present: a photo is needed, then a draft is saved with location and both IDs', async () => {
    serve();
    await markUrl('machine=0&entry=&revision=0');
    expect(await screen.findByText('Location found (±9 m)')).toBeOnTheScreen();
    expect(screen.getByText("Take the worker's photo first.")).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Save'));
    expect(saved()).toBeUndefined();
    await fireEvent.press(screen.getByText('Take photo'));
    await fireEvent.press(screen.getByText('Save'));
    expect(await screen.findByText('Saved as a draft. Submit the shift for approval from the team list.')).toBeOnTheScreen();
    expect(saved()).toMatchObject({
      employee: 'A', site: 'S1', shift: 'S1 Day', attendance_status: 'Present', work_mode: 'Not applicable', asset: null,
      photo: 'data:image/jpeg;base64,BBBB', revision: 0, latitude: 17.385, accuracy_m: 9,
    });
    expect(String(saved()!.request_id)).toMatch(/^[A-Za-z0-9_-]{16,80}$/);
    expect(String(saved()!.capture_id)).toMatch(/^[A-Za-z0-9_-]{16,80}$/);
  });

  it('Absent: a reason is needed; no photo is sent', async () => {
    serve();
    await markUrl('machine=0&entry=&revision=0');
    await screen.findByText('Location found (±9 m)');
    await fireEvent.press(screen.getByText('Absent'));
    expect(screen.getByText('Write the reason for the absence.')).toBeOnTheScreen();
    await fireEvent.changeText(screen.getByLabelText('Reason for absence (required)'), 'Sick');
    await fireEvent.press(screen.getByText('Save'));
    await screen.findByText('Saved as a draft. Submit the shift for approval from the team list.');
    expect(saved()).toMatchObject({ attendance_status: 'Absent', work_mode: 'Not applicable', remarks: 'Sick' });
    expect(saved()).not.toHaveProperty('photo');
  });

  it('a machine worker operating needs a machine of the site', async () => {
    serve();
    await markUrl('machine=1&entry=&revision=0');
    await screen.findByText('Location found (±9 m)');
    await fireEvent.press(screen.getByText('Take photo'));
    expect(screen.getByText('Choose the machine.')).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Excavator 1'));
    await fireEvent.press(screen.getByText('Save'));
    await screen.findByText('Saved as a draft. Submit the shift for approval from the team list.');
    expect(saved()).toMatchObject({ work_mode: 'Operating', asset: 'EXC-1' });
  });

  it('correcting a returned entry sends its name and revision; ERPNext refusals are shown', async () => {
    serve({ [`${HR_API}.save_capture`]: { status: 417, body: thrown('This record changed. Refresh before editing.') } });
    await markUrl('machine=0&entry=FAE-9&revision=3');
    await screen.findByText('Location found (±9 m)');
    await fireEvent.press(screen.getByText('Save'));
    expect(await screen.findByText('This record changed. Refresh before editing.')).toBeOnTheScreen();
    expect(saved()).toMatchObject({ name: 'FAE-9', revision: 3 });
  });
});
