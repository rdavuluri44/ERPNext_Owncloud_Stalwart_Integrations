import { fakeErp } from '@/__tests__/fake-erp';
import { HR_API, clock, currentShift, loadTodayAttendance } from '@/lib/attendance';

jest.mock('@/auth/session', () => ({ SignedOutError: class SignedOutError extends Error {}, useAuth: jest.fn() }));

const day = { name: 'Site 1 Day', start: '08:00', end: '20:00', label: 'Day' };
const night = { name: 'Site 1 Night', start: '20:00', end: '08:00', label: 'Night' };
const boot = {
  sites: [
    { name: 'S1', label: 'Site 1', supervisor: true, approver: true, shifts: [day, night] },
    { name: 'S2', label: 'Site 2', supervisor: false, approver: false, shifts: [day] },
  ],
  check_in_sites: [{ name: 'S1', label: 'Site 1', latitude: 17.385, longitude: 78.4867, radius_m: 200, maximum_accuracy_m: 50, shifts: [day, night] }],
};
const pending = (name: string) => ({ name, employee: 'W1', attendance_date: '2026-11-23', shift: day.name, attendance_status: 'Present', can_review: true });
const server = (over: Record<string, unknown> = {}) =>
  fakeErp({
    [`${HR_API}.bootstrap`]: { body: { message: boot } },
    [`${HR_API}.my_attendance`]: {
      body: { message: [{ name: 'E1', site: 'S1', attendance_date: '2026-11-23', state: 'Submitted', check_in_time: '2026-11-23 08:02:41' }] },
    },
    [`${HR_API}.team`]: { body: { message: { total: 15, missing: 3, attendance_date: '2026-11-23', workers: [] } } },
    [`${HR_API}.approvals`]: { body: { message: [pending('A'), pending('B')] } },
    ...over,
  });

describe('current shift', () => {
  it('finds the running shift, also across midnight', () => {
    expect(currentShift([day, night], '10:00')).toBe(day);
    expect(currentShift([day, night], '22:15')).toBe(night);
    expect(currentShift([day, night], '03:00')).toBe(night);
    expect(currentShift([day], '23:00')).toBe(day);
    expect(currentShift([], '10:00')).toBeNull();
  });
});

describe('Today attendance', () => {
  it('own check-in, team marking for the current shift, and what waits for approval', async () => {
    const { api, calls } = server();
    expect(await loadTodayAttendance(api, '10:00', '2026-11-23')).toMatchObject({
      self: { sites: ['Site 1'], today: expect.objectContaining({ state: 'Submitted', check_in_time: '2026-11-23 08:02:41' }) },
      teams: [{ siteId: 'S1', site: 'Site 1', shiftId: 'Site 1 Day', shift: 'Day', marked: 12, total: 15, counts: {}, drafts: 0 }],
      approvals: [{ siteId: 'S1', site: 'Site 1', count: 2, exceptions: 0, reviewable: 2 }],
    });
    expect(calls.filter((c) => c.method === `${HR_API}.team`).map((c) => c.args)).toEqual([{ site: 'S1', shift: 'Site 1 Day' }]);
    expect(calls.some((c) => c.args.site === 'S2')).toBe(false); // no role at Site 2: nothing asked
  });

  it("follows the header's choice: the chosen site and shift only", async () => {
    const { api, calls } = server();
    const data = await loadTodayAttendance(api, '10:00', '2026-11-23', { site: 'S1', shift: 'Site 1 Night' });
    expect(calls.filter((c) => c.method === `${HR_API}.team`).map((c) => c.args)).toEqual([{ site: 'S1', shift: 'Site 1 Night' }]);
    expect(data?.place?.site).toBe('S1');
    expect(data?.shift?.name).toBe('Site 1 Night');
    expect(data?.places.map((p) => [p.site, p.supervisor, p.approver, p.staff])).toEqual([
      ['S1', true, true, true],
      ['S2', false, false, false],
    ]);
    // a site where the person has no role there gives no cards
    const s2 = await loadTodayAttendance(server().api, '10:00', '2026-11-23', { site: 'S2', shift: null });
    expect(s2?.teams).toEqual([]);
    expect(s2?.approvals).toEqual([]);
  });

  it('no check-in yet today', async () => {
    const data = await loadTodayAttendance(server().api, '10:00', '2026-11-24');
    expect(data?.self).toEqual({ sites: ['Site 1'], today: null });
  });

  it('no attendance module on the server (not deployed yet): no cards', async () => {
    expect(await loadTodayAttendance(server({ [`${HR_API}.bootstrap`]: { status: 404, body: {} } }).api, '10:00', '2026-11-23')).toBeNull();
  });

  it('a person who does not check in themselves gets no check-in card, and empty counts are left out', async () => {
    const { api } = server({
      [`${HR_API}.bootstrap`]: { body: { message: { ...boot, check_in_sites: [] } } },
      [`${HR_API}.approvals`]: { body: { message: [] } },
    });
    const data = await loadTodayAttendance(api, '10:00', '2026-11-23');
    expect(data?.self).toBeNull();
    expect(data?.approvals).toEqual([]);
  });

  it('shows the time of day only', () => {
    expect(clock('2026-11-23 08:02:41')).toBe('08:02');
    expect(clock(null)).toBe('');
  });
});
