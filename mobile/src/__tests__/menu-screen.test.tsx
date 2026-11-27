import type { ReactNode } from 'react';
import { Text } from 'react-native';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import Menu from '@/app/(app)/menu';
import { HR_API } from '@/lib/attendance';
import { BOOT_PATH, clearErpCache } from '@/lib/erp';
import { memoryStore } from '@/lib/queue';
import { ThemeProvider } from '@/theme';

import { fakeErp } from './fake-erp';

const day = { name: 'Day1', start: '08:00', end: '20:00', label: 'Day' };
const boot = {
  sites: [
    { name: 'S1', label: 'Site 1', supervisor: true, approver: false, verifier: false, shifts: [day] },
    { name: 'S2', label: 'Site 2', supervisor: false, approver: true, verifier: true, shifts: [day] },
  ],
  check_in_sites: [],
};
let mockDown = false;
const mockErp = fakeErp({ [`${HR_API}.bootstrap`]: { body: { message: boot } } });
const mockApiRef = {
  current: async (path: string, init?: RequestInit) => {
    if (mockDown) throw new TypeError('Network request failed');
    if (path === BOOT_PATH) {
      return { ok: true, status: 200, json: async () => ({ message: { menus: [{ name: 'hr', label: 'Human Resources', app: 'hrms', items: [{ type: 'doctype', label: 'Leave Application', doctype: 'Leave Application' }] }] } }) } as Response;
    }
    return mockErp.api(path, init);
  },
};
// One object for every render, as the real session gives (a new one each render would reload forever).
const mockAuth = { api: (path: string, init?: RequestInit) => mockApiRef.current(path, init) };
jest.mock('@/auth/session', () => ({
  SignedOutError: class SignedOutError extends Error {},
  useAuth: () => mockAuth,
  useApiRef: () => mockApiRef,
}));
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStore: async () => mockStore }));
jest.mock('expo-secure-store', () => ({ getItemAsync: async () => null, setItemAsync: async () => {} }));

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const stub = (label: string) => {
  const Stub = () => <Text>{label}</Text>;
  Stub.displayName = label;
  return Stub;
};
const open = () =>
  renderRouter(
    { index: Menu, settings: stub('Settings screen'), 'attendance/team': stub('Team screen'), 'attendance/verify': stub('Verify screen'), 'attendance/approve': stub('Approve screen') },
    { initialUrl: '/', wrapper },
  );

describe('Menu', () => {
  beforeEach(async () => {
    mockDown = false;
    await mockStore.clear();
  });

  it('your work first, by role at each site; then the ERPNext lists; then Settings', async () => {
    const router = await open();
    expect(await screen.findByText('Mark attendance')).toBeOnTheScreen();
    expect(screen.getByText('Verify attendance')).toBeOnTheScreen();
    expect(screen.getByText('Approve attendance')).toBeOnTheScreen();
    expect(screen.queryByText('Check in or out')).toBeNull(); // not set up for own check-in
    expect(await screen.findByText('Human Resources')).toBeOnTheScreen();
    expect(screen.getByText('1 list')).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Verify attendance'));
    expect(router.getPathname()).toBe('/attendance/verify');
    expect(router.getSearchParams()).toMatchObject({ site: 'S2' });
  });

  it('offline: your work still listed from the saved copy; the ERPNext lists say they need a connection', async () => {
    const first = await open();
    await screen.findByText('Mark attendance'); // online once: saved
    await first.unmount();
    clearErpCache(); // as after an app restart without signal
    mockDown = true;
    await open();
    expect(await screen.findByText('Mark attendance')).toBeOnTheScreen();
    expect(await screen.findByText(/^ERPNext lists need a connection/)).toBeOnTheScreen();
    expect(screen.getByText('Settings')).toBeOnTheScreen();
  });
});
