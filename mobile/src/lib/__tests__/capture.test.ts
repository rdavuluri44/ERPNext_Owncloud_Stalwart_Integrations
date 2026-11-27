import { distanceM, fenceProblem, localStamp, offlineFields, parseStamp, photoDataUrl, rememberServerClock } from '@/lib/capture';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));
const mockSaved = new Map<string, string>();
jest.mock('expo-secure-store', () => ({
  getItemAsync: async (k: string) => mockSaved.get(k) ?? null,
  setItemAsync: async (k: string, v: string) => void mockSaved.set(k, v),
}));
let mockBase64: string | undefined = 'QUJD';
jest.mock('expo-image-manipulator', () => ({
  ImageManipulator: {
    manipulate: () => ({
      resize: () => ({
        renderAsync: async () => ({ saveAsync: async () => ({ uri: 'file:///cache/small.jpg', base64: mockBase64 }) }),
      }),
    }),
  },
  SaveFormat: { JPEG: 'jpeg' },
}));
const mockDeleted: string[] = [];
jest.mock('expo-file-system', () => ({
  Paths: { cache: { uri: 'file:///cache/' } },
  File: function MockFile(this: { delete: () => void }, mockUri: string) {
    this.delete = () => void mockDeleted.push(mockUri);
  },
}));
jest.mock('expo-location', () => ({}));

const site = { latitude: 17.385, longitude: 78.4867, radius_m: 200, maximum_accuracy_m: 50 };
const fix = (latitude: number, longitude: number, accuracy_m = 10) => ({ latitude, longitude, accuracy_m, gps_captured_at: '' });

describe('fence check, the same rule as the server', () => {
  it('measures like custom_hr (haversine, Earth radius 6371 km)', () => {
    // 0.001 degree of latitude is 111.19 m with R = 6371000 (Python: 6371000*2*asin(sqrt(sin(radians(0.001)/2)**2)))
    expect(distanceM(17, 78, 17.001, 78)).toBeCloseTo(111.19, 1);
  });

  it('refuses poor accuracy and a point outside the radius, with no allowance for accuracy', () => {
    expect(fenceProblem(fix(17.385, 78.4867, 60), site)).toContain('not accurate enough (60 m; this site allows 50 m)');
    expect(fenceProblem(fix(17.385, 78.4867), site)).toBeNull();
    const justOutside = 17.385 + 200.5 / 111194.9; // 200.5 m north: outside a 200 m radius, as on the server
    expect(fenceProblem(fix(justOutside, 78.4867, 1), site)).toContain('the allowed area is 200 m');
    const justInside = 17.385 + 199.5 / 111194.9;
    expect(fenceProblem(fix(justInside, 78.4867, 1), site)).toBeNull();
  });

  it('a site without a radius only checks accuracy', () => {
    expect(fenceProblem(fix(0, 0), { ...site, radius_m: 0 })).toBeNull();
  });
});

describe('times', () => {
  it('writes and reads phone-local ERPNext datetimes', () => {
    const d = new Date(2026, 10, 23, 8, 2, 41);
    expect(localStamp(d)).toBe('2026-11-23 08:02:41');
    expect(parseStamp('2026-11-23 08:02:41.123456')?.getTime()).toBe(d.getTime());
    expect(parseStamp('garbage')).toBeNull();
  });

  it('remembers the server clock and puts the corrected time fields on an offline capture', async () => {
    // server 2 minutes ahead of the phone
    await rememberServerClock('2026-11-23 08:04:41.000000', new Date(2026, 10, 23, 8, 2, 41));
    expect(mockSaved.get('server-clock-offset-s')).toBe('120');
    expect(await offlineFields(new Date(2026, 10, 23, 9, 0, 0))).toEqual({
      offline: 1,
      device_captured_at: '2026-11-23 09:00:00',
      clock_offset_s: 120,
    });
  });
});

describe('photos never stay on the phone as files', () => {
  beforeEach(() => {
    mockDeleted.length = 0;
  });

  it('returns the shrunk photo as a data URL and deletes the camera file and the shrunk file', async () => {
    mockBase64 = 'QUJD';
    expect(await photoDataUrl('file:///cache/camera.jpg')).toBe('data:image/jpeg;base64,QUJD');
    expect(mockDeleted).toEqual(['file:///cache/camera.jpg', 'file:///cache/small.jpg']);
  });

  it('deletes both files also when shrinking fails', async () => {
    mockBase64 = undefined;
    await expect(photoDataUrl('file:///cache/camera.jpg')).rejects.toThrow();
    expect(mockDeleted).toEqual(['file:///cache/camera.jpg', 'file:///cache/small.jpg']);
  });
});

describe("only the app own copies are deleted", () => {
  it('a file outside the app cache (a gallery original) is never deleted', async () => {
    mockDeleted.length = 0;
    mockBase64 = 'QUJD';
    await photoDataUrl('content://media/external/images/1');
    expect(mockDeleted).toEqual(['file:///cache/small.jpg']);
  });
});
