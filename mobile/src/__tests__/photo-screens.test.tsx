import type { ReactNode } from 'react';
import { Text } from 'react-native';
import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';

import Documents from '@/app/documents/index';
import AddPhoto from '@/app/photos/add';
import Gallery from '@/app/photos/index';
import { HR_API } from '@/lib/attendance';
import { PHOTO_API, cachedPreview, keepPreview } from '@/lib/photos';
import { memoryStore } from '@/lib/queue';
import { ThemeProvider } from '@/theme';

import { type Answer, fakeErp } from './fake-erp';

const day = { name: 'Day1', start: '00:00', end: '23:59', label: 'Day' };
const boot = {
  sites: [{ name: 'S1', label: 'Site 1', project: 'P1', project_name: 'Project 1', supervisor: true, approver: false, shifts: [day] }],
  check_in_sites: [],
};
const photo = (n: number, extra: Record<string, unknown> = {}) => ({
  name: `DP-${n}`, project: 'P1', site: 'S1', kind: 'Progress', taken_at: '2026-11-24 10:15:30', taken_by: 'a@example.com', ...extra,
});
let mockDown = false;
let answers: Record<string, Answer | ((args: Record<string, unknown>) => Answer)> = {};
let mockErp = fakeErp(answers);
const serve = (over: typeof answers = {}) => {
  answers = {
    [`${HR_API}.bootstrap`]: { body: { message: boot } },
    [`${PHOTO_API}.upload_photo`]: (args) => ({ body: { message: { name: 'DP-9', path: `Site 1/x-${(args.payload as { client_id: string }).client_id}.jpg` } } }),
    [`${PHOTO_API}.photos`]: { body: { message: [photo(1), photo(2, { kind: 'Hindrance', from_gallery: 1 })] } },
    [`${PHOTO_API}.files`]: (args) => ({
      body: {
        message: args.path
          ? [{ name: 'a.jpg', path: `${String(args.path)}/a.jpg`, folder: false, size: 2048 }]
          : [
              { name: 'Site 1', path: 'Site 1', folder: true, size: 0 },
              { name: 'plan.pdf', path: 'plan.pdf', folder: false, size: 3145728, modified: 'Mon, 24 Nov 2026 10:00:00 GMT' },
            ],
      },
    }),
    ...over,
  };
  mockErp = fakeErp(answers);
  return mockErp.calls;
};
const mockApiRef = {
  current: async (...a: Parameters<ReturnType<typeof fakeErp>['api']>) => {
    if (mockDown) throw new TypeError('Network request failed');
    return mockErp.api(...a);
  },
};
jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useApiRef: () => mockApiRef }));
const mockStore = memoryStore();
jest.mock('@/lib/offline-store', () => ({ offlineStore: async () => mockStore }));
jest.mock('expo-secure-store', () => ({ getItemAsync: async () => null, setItemAsync: async () => {} }));
jest.mock('expo-crypto', () => ({ randomUUID: () => 'photo-0000-0000-0001' }));
jest.mock('expo-location', () => ({}));
jest.mock('expo-image-manipulator', () => ({ ImageManipulator: {}, SaveFormat: { JPEG: 'jpeg' } }));
jest.mock('@/lib/capture', () => ({
  ...jest.requireActual('@/lib/capture'),
  getFix: async () => ({ latitude: 17.385, longitude: 78.486, accuracy_m: 8, gps_captured_at: '2026-11-24 10:15:00' }),
  photoDataUrl: async () => 'data:image/jpeg;base64,R0FMTA==',
  offlineFields: async () => ({ offline: 1, device_captured_at: '2026-11-24 10:15:30', clock_offset_s: 0 }),
}));
let mockPicked = true;
jest.mock('expo-image-picker', () => ({
  requestMediaLibraryPermissionsAsync: async () => ({ granted: true }),
  launchImageLibraryAsync: async () => (mockPicked ? { canceled: false, assets: [{ uri: 'file:///cache/pick.jpg' }] } : { canceled: true, assets: [] }),
}));
jest.mock('@/components/photo-taker', () => {
  const { createElement } = jest.requireActual('react');
  const RN = jest.requireActual('react-native');
  return {
    PhotoTaker: ({ onPhoto }: { onPhoto: (p: string) => void }) =>
      createElement(RN.Pressable, { onPress: () => onPhoto('data:image/jpeg;base64,Q0FN') }, createElement(RN.Text, null, 'Take test photo')),
  };
});

const wrapper = ({ children }: { children: ReactNode }) => <ThemeProvider>{children}</ThemeProvider>;
const stub = (label: string) => {
  const Stub = () => <Text>{label}</Text>;
  Stub.displayName = label;
  return Stub;
};
const uploads = () => mockErp.calls.filter((c) => c.method === `${PHOTO_API}.upload_photo`).map((c) => c.args.payload as Record<string, unknown>);

describe('add a site photo', () => {
  beforeEach(async () => {
    mockDown = false;
    mockPicked = true;
    await mockStore.clear();
  });
  const open = () => renderRouter({ 'photos/add': AddPhoto }, { initialUrl: '/photos/add', wrapper });

  it('camera photo: site, type, location and remarks go to the project folder', async () => {
    serve();
    await open();
    await fireEvent.press(await screen.findByText('Hindrance'));
    await fireEvent.press(screen.getByText('Take test photo'));
    await fireEvent.changeText(screen.getByLabelText('Remarks (optional)'), 'Slab ready');
    await fireEvent.press(screen.getByText('Save to project folder'));
    expect(await screen.findByText('Saved to the project folder.')).toBeOnTheScreen();
    expect(uploads()).toEqual([
      expect.objectContaining({ site: 'S1', kind: 'Hindrance', photo: 'data:image/jpeg;base64,Q0FN', from_gallery: 0, remarks: 'Slab ready', latitude: 17.385, accuracy_m: 8 }),
    ]);
  });

  it('gallery photo: marked "From gallery", sent without the phone location', async () => {
    serve();
    await open();
    await fireEvent.press(await screen.findByText('Choose from gallery'));
    expect(await screen.findByText('From gallery: it is marked so in the project folder.')).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Save to project folder'));
    await screen.findByText('Saved to the project folder.');
    const sent = uploads()[0];
    expect(sent).toMatchObject({ from_gallery: 1, photo: 'data:image/jpeg;base64,R0FMTA==' });
    expect(sent.latitude).toBeUndefined();
  });

  it('offline: kept in the encrypted queue and sent later', async () => {
    serve();
    await open();
    await fireEvent.press(await screen.findByText('Take test photo'));
    mockDown = true;
    await fireEvent.press(screen.getByText('Save to project folder'));
    expect(await screen.findByText(/^Saved on this phone/)).toBeOnTheScreen();
    expect(await mockStore.all()).toEqual([expect.objectContaining({ method: `${PHOTO_API}.upload_photo`, state: 'waiting' })]);
  });

  it('nothing is sent without a photo', async () => {
    serve();
    await open();
    await fireEvent.press(await screen.findByText('Save to project folder'));
    expect(uploads()).toEqual([]);
  });
});

describe('site photos', () => {
  beforeEach(() => {
    mockDown = false;
  });
  const open = () => renderRouter({ 'photos/index': Gallery, 'photos/[name]': stub('Photo screen'), 'photos/add': stub('Add screen') }, { initialUrl: '/photos', wrapper });

  it('lists the photos ERPNext allows, filters by type, and opens one with its details', async () => {
    const calls = serve();
    const router = await open();
    expect(await screen.findByLabelText('Progress photo at Site 1, 24-11-2026 10:15')).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Hindrance'));
    expect(calls.filter((c) => c.method === `${PHOTO_API}.photos`).at(-1)?.args).toMatchObject({ kind: 'Hindrance' });
    await fireEvent.press(screen.getByLabelText('Hindrance photo at Site 1, 24-11-2026 10:15'));
    expect(router.getPathname()).toBe('/photos/DP-2');
    expect(router.getSearchParams()).toMatchObject({ gallery: '1', site: 'Site 1' });
  });
});

describe('project files', () => {
  beforeEach(() => {
    mockDown = false;
  });
  const open = (url = '/documents') => renderRouter({ 'documents/index': Documents, 'photos/[name]': stub('Photo screen') }, { initialUrl: url, wrapper });

  it('folders first; a folder opens; other files say where they open', async () => {
    const calls = serve();
    const router = await open();
    expect(await screen.findByText('Site 1')).toBeOnTheScreen();
    expect(screen.getByText(/^3\.0 MB · .* · opens in Drive on a computer$/)).toBeOnTheScreen();
    await fireEvent.press(screen.getByText('Site 1'));
    expect(router.getSearchParams()).toMatchObject({ project: 'P1', path: 'Site 1' });
    expect(calls.find((c) => c.method === `${PHOTO_API}.files`)?.args).toEqual({ project: 'P1', path: '' });
  });
});

describe('previews in memory', () => {
  it('keeps the last 100 only', () => {
    for (let i = 0; i < 105; i++) keepPreview(`k${i}`, `d${i}`);
    expect(cachedPreview('k0')).toBeNull();
    expect(cachedPreview('k104')).toBe('d104');
  });
});
