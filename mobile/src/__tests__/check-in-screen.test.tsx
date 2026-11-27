import type { ReactNode } from 'react';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import CheckIn from '@/app/attendance/check-in';
import { HR_API } from '@/lib/attendance';
import { localToday } from '@/lib/format';
import { memoryStore } from '@/lib/queue';
import { ThemeProvider } from '@/theme';

import { type Answer, fakeErp, thrown } from './fake-erp';

const site = { name: 'S1', label: 'Site 1', latitude: 17.385, longitude: 78.4867, radius_m: 200, maximum_accuracy_m: 50, shifts: [{ name: 'S1 Day', start: '00:00', end: '23:59', label: 'Day' }] };
let mockAnswers: Record<string, Answer> = {};
const mockApiRef = { current: (...a: Parameters<ReturnType<typeof fakeErp>['api']>) => mockErp.api(...a) };
let mockErp = fakeErp({});
const serve = (over: Record<string, Answer> = {}) => {
  mockAnswers = {
    [`${HR_API}.bootstrap`]: { body: { message: { server_now: '2026-11-23 08:00:00', sites: [], check_in_sites: [site] } } },
    [`${HR_API}.my_attendance`]: { body: { message: [] } },
    [`${HR_API}.self_check_in`]: { body: { message: { name: 'E1', state: 'Submitted', check_in_time: '2026-11-23 08:02:41' } } },
    [`${HR_API}.self_check_out`]: { body: { message: { name: 'E1', check_out_time: '2026-11-23 17:30:00' } } },
    ...over,
  };
  mockErp = fakeErp(mockAnswers);
  return mockErp.calls;
};
jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useApiRef: () => mockApiRef }));
let mockFix = { latitude: 17.385, longitude: 78.4867, accuracy_m: 12.4, gps_captured_at: '2026-11-23 08:02:40' };
jest.mock('@/lib/capture', () => ({
  ...jest.requireActual('@/lib/capture'),
  getFix: async () => mockFix,
  rememberServerClock: async () => {},
  offlineFields: async () => ({ offline: 1, device_captured_at: '2026-11-23 08:02:41', clock_offset_s: 0 }),
}));
jest.mock('expo-image-manipulator', () => ({ ImageManipulator: {}, SaveFormat: { JPEG: 'jpeg' } }));
jest.mock('expo-location', () => ({}));
jest.mock('expo-crypto', () => ({ randomUUID: () => 'id-0000-0000-0000-0001' }));
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
      createElement(Pressable, { onPress: () => onPhoto('data:image/jpeg;base64,AAAA') }, createElement(Text, null, 'Take photo')),
  };
});
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStore: async () => mockStore }));

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const open = () => renderRouter({ 'attendance/check-in': CheckIn }, { initialUrl: '/attendance/check-in', wrapper });

describe('own check-in', () => {
  beforeEach(async () => {
    await mockStore.clear();
    mockFix = { latitude: 17.385, longitude: 78.4867, accuracy_m: 12.4, gps_captured_at: '2026-11-23 08:02:40' };
  });

  it('selfie, location inside the fence, then check-in with one client ID', async () => {
    const calls = serve();
    await open();
    expect(await screen.findByText('Site 1')).toBeOnTheScreen();
    expect(await screen.findByText('Location found (±12 m)')).toBeOnTheScreen();
    expect(screen.getByText('Take your selfie first.')).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Take photo'));
    await fireEvent.press(screen.getByText('Check in'));
    expect(await screen.findByText('Checked in at 08:02. Sent to your approver.')).toBeOnTheScreen();
    const sent = calls.find((c) => c.method === `${HR_API}.self_check_in`)!;
    expect(sent.post).toBe(true);
    expect(sent.args).toEqual({
      payload: {
        site: 'S1',
        shift: 'S1 Day',
        request_id: 'id-0000-0000-0000-0001',
        photo: 'data:image/jpeg;base64,AAAA',
        latitude: 17.385,
        longitude: 78.4867,
        accuracy_m: 12.4,
        gps_captured_at: '2026-11-23 08:02:40',
      },
    });
  });

  it('without a selfie nothing is sent', async () => {
    const calls = serve();
    await open();
    await screen.findByText('Location found (±12 m)');
    await fireEvent.press(screen.getByText('Check in'));
    expect(calls.some((c) => c.method === `${HR_API}.self_check_in`)).toBe(false);
    expect(screen.getByText('Take your selfie first.')).toBeOnTheScreen();
  });

  it('outside the fence: says so and sends nothing', async () => {
    const calls = serve();
    mockFix = { ...mockFix, latitude: 17.395 }; // about 1.1 km north
    await open();
    expect(await screen.findByText(/the allowed area is 200 m/)).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Take photo'));
    await fireEvent.press(screen.getByText('Check in'));
    expect(calls.some((c) => c.method === `${HR_API}.self_check_in`)).toBe(false);
  });

  it("shows ERPNext's refusal as it gives it", async () => {
    serve({ [`${HR_API}.self_check_in`]: { status: 417, body: thrown('You have already checked in for this shift.') } });
    await open();
    await screen.findByText('Location found (±12 m)');
    await fireEvent.press(screen.getByText('Take photo'));
    await fireEvent.press(screen.getByText('Check in'));
    expect(await screen.findByText('You have already checked in for this shift.')).toBeOnTheScreen();
  });

  it('already checked in today: check-out, no selfie', async () => {
    const calls = serve({
      [`${HR_API}.my_attendance`]: {
        body: { message: [{ name: 'E1', site: 'S1', attendance_date: localToday(), state: 'Submitted', check_in_time: '2026-11-23 08:02:41' }] },
      },
    });
    await open();
    expect(await screen.findByText('You checked in at 08:02 (Submitted).')).toBeOnTheScreen();
    expect(screen.queryByText('Take photo')).toBeNull();
    await screen.findByText('Location found (±12 m)');
    await fireEvent.press(screen.getByText('Check out'));
    expect(await screen.findByText('Checked out at 17:30.')).toBeOnTheScreen();
    const out = calls.find((c) => c.method === `${HR_API}.self_check_out`)!;
    expect(out.args).toEqual({ payload: { name: 'E1', ...mockFix } });
  });

  it('no connection: the check-in is kept on the phone and the person is told', async () => {
    serve();
    const online = mockErp.api;
    mockErp = { ...mockErp, api: async (path, init) => {
      if (path.includes('self_check_in')) throw new TypeError('Network request failed');
      return online(path, init);
    } };
    await open();
    await screen.findByText('Location found (±12 m)');
    await fireEvent.press(screen.getByText('Take photo'));
    await fireEvent.press(screen.getByText('Check in'));
    expect(await screen.findByText('No connection: your check-in is saved on this phone and will be sent by itself.')).toBeOnTheScreen();
    const [kept] = await mockStore.all();
    expect(kept.id).toBe('id-0000-0000-0000-0001');
    expect((kept.args.payload as Record<string, unknown>).offline).toBe(1);
  });
});
