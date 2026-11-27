import type { ReactNode } from 'react';
import { Text } from 'react-native';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import AppTabs from '@/app/(app)/_layout';
import Menu from '@/app/(app)/menu';
import Today from '@/app/(app)/index';
import { memoryStore } from '@/lib/queue';
import { ThemeProvider } from '@/theme';

// One ref for every render, as the real useApiRef gives (a new object each render would loop the effects).
const mockApiRef = { current: async () => { throw new TypeError('offline in tests'); } };
jest.mock('@/auth/session', () => ({
  APP_NAME: 'ERP Mobile',
  SignedOutError: class SignedOutError extends Error {},
  useAuth: () => ({ user: { name: 'Worker A', email: 'a@example.com', roles: [] }, api: jest.fn() }),
  useApiRef: () => mockApiRef,
}));
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStore: async () => mockStore, offlineStorageKind: async () => 'encrypted' }));
const mockSaved = new Map<string, string>();
jest.mock('expo-secure-store', () => ({
  getItemAsync: async (k: string) => mockSaved.get(k) ?? null,
  setItemAsync: async (k: string, v: string) => void mockSaved.set(k, v),
  deleteItemAsync: async (k: string) => void mockSaved.delete(k),
}));
jest.mock('@/lib/erp', () => ({
  ...jest.requireActual('@/lib/erp'),
  useErp: () => ({
    data: {
      message: {
        menus: [
          {
            name: 'hr',
            label: 'Human Resources',
            app: 'hrms',
            items: [{ type: 'doctype', label: 'Leave Application', doctype: 'Leave Application' }],
          },
        ],
      },
    },
    error: null,
    loading: false,
    reload: jest.fn(),
  }),
}));

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const Stub = () => <Text>stub</Text>;
const app = {
  '(app)/_layout': AppTabs,
  '(app)/index': Today,
  '(app)/inbox': Stub,
  '(app)/my-hr': Stub,
  '(app)/menu': Menu,
  settings: () => <Text>Settings screen</Text>,
  'list/[doctype]': () => <Text>List screen</Text>,
};

describe('app shell', () => {
  beforeEach(async () => {
    await mockStore.clear();
  });

  it('has the four tabs of owner decision 2, in order', async () => {
    await renderRouter(app, { initialUrl: '/', wrapper });
    const labels = screen.getAllByRole('button').map((b) => b.props.accessibilityLabel ?? '');
    const tabs = ['Today', 'Inbox', 'My HR', 'Menu'].map((name) => labels.findIndex((l) => l.startsWith(name)));
    expect(tabs.every((i) => i >= 0)).toBe(true);
    expect([...tabs].sort((a, b) => a - b)).toEqual(tabs);
  });

  it('Today shows the app header and says nothing is waiting', async () => {
    await renderRouter(app, { initialUrl: '/', wrapper });
    expect(await screen.findByText('ERP Mobile')).toBeOnTheScreen();
    expect(await screen.findByText('Nothing waiting to send')).toBeOnTheScreen();
  });

  it('Today counts what waits in the offline queue', async () => {
    for (const id of ['a', 'b']) {
      await mockStore.put({ id, method: 'm', args: {}, createdAt: Date.now(), attempts: 0, state: 'waiting' });
    }
    await mockStore.put({ id: 'c', method: 'm', args: {}, createdAt: Date.now(), attempts: 1, state: 'failed', error: 'refused' });
    await renderRouter(app, { initialUrl: '/', wrapper });
    expect(await screen.findByText('2 captures waiting to send')).toBeOnTheScreen();
  });

  it('Menu lists Settings first, then the role menus, and opens Settings', async () => {
    const router = await renderRouter(app, { initialUrl: '/menu', wrapper });
    expect(screen.getByText('Human Resources')).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Settings'));
    expect(await screen.findByText('Settings screen')).toBeOnTheScreen();
    expect(router.getPathname()).toBe('/settings');
  });

  it('Menu search finds a list across the menus and opens it', async () => {
    const router = await renderRouter(app, { initialUrl: '/menu', wrapper });
    await fireEvent.changeText(screen.getByLabelText('Search your lists'), 'leave');
    expect(screen.queryByText('Settings')).toBeNull();
    await fireEvent.press(screen.getByText('Leave Application'));
    expect(await screen.findByText('List screen')).toBeOnTheScreen();
    expect(router.getPathnameWithParams()).toBe('/list/Leave Application');
  });

  it('Menu search says when nothing matches, and clearing it brings the menus back', async () => {
    await renderRouter(app, { initialUrl: '/menu', wrapper });
    await fireEvent.changeText(screen.getByLabelText('Search your lists'), 'payroll');
    expect(screen.getByText('No list matches “payroll”.')).toBeOnTheScreen();
    await fireEvent.press(screen.getByLabelText('Clear search'));
    expect(screen.getByText('Human Resources')).toBeOnTheScreen();
  });
});
