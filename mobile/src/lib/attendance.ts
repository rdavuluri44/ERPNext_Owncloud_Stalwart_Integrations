// Attendance for Today (step T2): the person's own check-in, their team's marking, and what waits for their
// approval, from the custom_hr API (erpnext_drive_integrations.custom_hr.api, PR #38/#39). The server decides
// every role, site and shift; the app only counts and shows. Read only: the check-in, team and bulk-approval
// screens come with the attendance pilot (build guide phase 3).
import { z } from 'zod';

import { rememberServerClock } from '@/lib/capture';
import type { Api } from '@/lib/erp';
import { callKept } from '@/lib/saved';

export const HR_API = 'erpnext_drive_integrations.custom_hr.api';

const ShiftSchema = z.object({
  name: z.string(),
  start: z.string(),
  end: z.string(),
  label: z.string().nullish(),
  attendance_date: z.string().nullish(),
});
const CheckInSite = z.object({
  name: z.string(),
  label: z.string(),
  project: z.string().nullish(),
  latitude: z.number().nullish(),
  longitude: z.number().nullish(),
  radius_m: z.number().nullish(),
  maximum_accuracy_m: z.number().nullish(),
  shifts: z.array(ShiftSchema),
});
export type CheckInSiteT = z.infer<typeof CheckInSite>;
export const Boot = z.object({
  server_now: z.string().nullish(),
  sites: z.array(
    z.object({
      name: z.string(),
      label: z.string(),
      project: z.string().nullish(),
      project_name: z.string().nullish(),
      supervisor: z.boolean(),
      approver: z.boolean(),
      /** Engineer: checks the attendance of the supervisors under them before the PM approves. */
      verifier: z.boolean().default(false),
      shifts: z.array(ShiftSchema),
      assets: z.array(z.object({ name: z.string(), label: z.string() })).default([]),
      supervisors: z.array(z.object({ user: z.string(), label: z.string() })).default([]),
    }),
  ),
  check_in_sites: z.array(CheckInSite),
});
export type BootT = z.infer<typeof Boot>;

/** The attendance bootstrap; also remembers the server's clock for offline captures. */
export async function loadBoot(api: Api): Promise<BootT> {
  const boot = await callKept(api, `${HR_API}.bootstrap`, Boot);
  if (boot.server_now) await rememberServerClock(boot.server_now);
  return boot;
}
export const Mine = z.array(
  z.object({
    name: z.string(),
    site: z.string(),
    attendance_date: z.string(),
    state: z.string(),
    check_in_time: z.string().nullish(),
    check_out_time: z.string().nullish(),
  }),
);
/** How many workers are in each state (Not recorded, Draft, Submitted, Returned, Approved). */
export function stateCounts(workers: { state: string }[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const w of workers) counts[w.state] = (counts[w.state] ?? 0) + 1;
  return counts;
}

/** The site's shift running at `now` ("HH:MM", phone time; for choosing a card only, never for a record). */
export function currentShift<S extends { start: string; end: string }>(shifts: S[], now: string): S | null {
  const within = (s: S) => (s.start <= s.end ? now >= s.start && now < s.end : now >= s.start || now < s.end);
  return shifts.find(within) ?? shifts[0] ?? null;
}

// ---- the header's places (project > Field Site > shift) ----
export type Shift = { name: string; start: string; end: string; label?: string | null };
export type Place = {
  site: string;
  siteLabel: string;
  project: string;
  projectLabel: string;
  shifts: Shift[];
  /** The person's roles at this site, as custom_hr's bootstrap says. */
  supervisor: boolean;
  approver: boolean;
  verifier: boolean;
  staff: boolean;
};

/** Every site the person may work at (as supervisor, approver or staff), each with its project. */
export function placesFrom(boot: BootT): Place[] {
  const byName = new Map<string, Place>();
  for (const s of boot.sites) {
    byName.set(s.name, {
      site: s.name,
      siteLabel: s.label,
      project: s.project ?? '',
      projectLabel: s.project_name || s.project || '',
      shifts: s.shifts,
      supervisor: s.supervisor,
      approver: s.approver,
      verifier: s.verifier,
      staff: false,
    });
  }
  for (const s of boot.check_in_sites) {
    const known = byName.get(s.name);
    if (known) known.staff = true;
    else {
      byName.set(s.name, {
        site: s.name,
        siteLabel: s.label,
        project: s.project ?? '',
        projectLabel: s.project ?? '',
        shifts: s.shifts,
        supervisor: false,
        approver: false,
        verifier: false,
        staff: true,
      });
    }
  }
  return [...byName.values()].sort((a, b) => a.projectLabel.localeCompare(b.projectLabel) || a.siteLabel.localeCompare(b.siteLabel));
}

/** The projects, each once, in order. */
export const projectsOf = (places: Place[]) =>
  [...new Map(places.map((p) => [p.project, { project: p.project, label: p.projectLabel }])).values()];

/** The chosen place, falling back to the first site and its running shift if the choice is gone. */
export function resolvePlace(places: Place[], c: { site: string | null; shift: string | null }, now: string): { place: Place; shift: Shift | null } | null {
  const place = places.find((p) => p.site === c.site) ?? places[0];
  if (!place) return null;
  const shift = place.shifts.find((s) => s.name === c.shift) ?? currentShift(place.shifts, now);
  return { place, shift };
}


export type TodayAttendance = {
  places: Place[];
  place: Place | null;
  shift: Shift | null;
  /** Only for people who check in themselves (listed as Staff on a site). */
  self: { sites: string[]; today: z.infer<typeof Mine>[number] | null } | null;
  teams: {
    siteId: string;
    site: string;
    shiftId: string;
    shift: string;
    marked: number;
    total: number;
    counts: Record<string, number>;
    /** Own drafts still to submit for approval. */
    drafts: number;
    /** Workers this person may mark (their own) that are not marked yet or were returned. */
    toMark: number;
    /** Workers this person may mark or edit at all; 0 for an approver whose site has other supervisors. */
    mine: number;
  }[];
  approvals: { siteId: string; site: string; count: number; exceptions: number; reviewable: number }[];
  /** Engineer: entries waiting for their check (Pending Verification) per site. */
  checks: { siteId: string; site: string; count: number }[];
};

/**
 * Null when the server has no attendance module (not deployed yet) or answers otherwise: Today then simply
 * shows no attendance cards.
 */
export async function loadTodayAttendance(
  api: Api,
  now: string,
  today: string,
  choice: { site: string | null; shift: string | null } = { site: null, shift: null },
): Promise<TodayAttendance | null> {
  let boot: BootT;
  try {
    boot = await loadBoot(api);
  } catch {
    return null;
  }
  const places = placesFrom(boot);
  const chosen = resolvePlace(places, choice, now);
  const here = (site: string) => !chosen || chosen.place.site === site;
  const [mine, teams, approvals, checks] = await Promise.all([
    boot.check_in_sites.length
      ? callKept(api, `${HR_API}.my_attendance`, Mine).catch(() => null) // unknown offline: no strip
      : Promise.resolve(null),
    Promise.all(
      boot.sites
        .filter((s) => s.supervisor && here(s.name))
        .map(async (s) => {
          const shift = chosen?.place.site === s.name && chosen.shift ? chosen.shift : currentShift(s.shifts, now);
          if (!shift) return null;
          try {
            const team = await callKept(api, `${HR_API}.team`, TeamList, { site: s.name, shift: shift.name });
            return {
              siteId: s.name,
              site: s.label,
              shiftId: shift.name,
              shift: shift.label ?? shift.name,
              marked: team.total - team.missing,
              total: team.total,
              counts: stateCounts(team.workers),
              drafts: team.workers.filter((w) => w.state === 'Draft' && w.can_edit && w.entry).length,
              toMark: team.workers.filter((w) => w.can_capture && (w.state === 'Not recorded' || w.state === 'Returned')).length,
              mine: team.workers.filter((w) => w.can_capture || w.can_edit).length,
            };
          } catch {
            return null;
          }
        }),
    ),
    Promise.all(
      boot.sites
        .filter((s) => s.approver && here(s.name))
        .map(async (s) => {
          try {
            // Only what this person may review counts (maintainers' fix on main, f26c4ca).
            const list = (await callKept(api, `${HR_API}.approvals`, Pending, { site: s.name })).filter((e) => e.can_review);
            return {
              siteId: s.name,
              site: s.label,
              count: list.length,
              exceptions: list.filter((e) => !!e.captured_offline || e.attendance_status === 'Absent').length,
              reviewable: list.length,
            };
          } catch {
            return null;
          }
        }),
    ),
    Promise.all(
      boot.sites
        .filter((s) => s.verifier && here(s.name))
        .map(async (s) => {
          try {
            const list = await callKept(api, `${HR_API}.verifications`, ToVerify, { site: s.name });
            return { siteId: s.name, site: s.label, count: list.length };
          } catch {
            return null;
          }
        }),
    ),
  ]);
  return {
    places,
    place: chosen?.place ?? null,
    shift: chosen?.shift ?? null,
    self: mine
      ? { sites: boot.check_in_sites.map((s) => s.label), today: mine.find((m) => m.attendance_date === today) ?? null }
      : null,
    teams: teams.filter((t): t is NonNullable<typeof t> => t !== null && t.total > 0),
    approvals: approvals.filter((a): a is NonNullable<typeof a> => a !== null && a.count > 0),
    checks: checks.filter((c): c is NonNullable<typeof c> => c !== null && c.count > 0),
  };
}

/** "08:02" from ERPNext's "2026-11-23 08:02:41". */
export const clock = (value?: string | null) => /(\d{2}:\d{2})/.exec(value ?? '')?.[1] ?? '';

// ---- team marking (supervisor, P3c): custom_hr's `team` answer ----
export const Worker = z.object({
  employee: z.string(),
  employee_name: z.string().nullish(),
  designation: z.string().nullish(),
  machine_required: z.coerce.number().nullish(),
  /** The worker's supervisor (user); only they can mark the worker. */
  supervisor: z.string().nullish(),
  state: z.string(),
  entry: z.string().nullish(),
  revision: z.number().nullish(),
  can_capture: z.boolean(),
  can_edit: z.boolean(),
});
export type WorkerT = z.infer<typeof Worker>;
export const TeamList = z.object({
  workers: z.array(Worker),
  total: z.number(),
  missing: z.number(),
  attendance_date: z.string(),
  truncated: z.boolean().nullish(),
});

/** Entries this supervisor still has to submit for approval (their own drafts). */
export const drafts = (workers: WorkerT[]) => workers.filter((w) => w.state === 'Draft' && w.can_edit && w.entry);

// ---- approval (PM, P3d): custom_hr's `approvals`, `entry` and `review_many` answers ----
export const Pending = z.array(
  z.object({
    name: z.string(),
    employee: z.string(),
    employee_name: z.string().nullish(),
    attendance_date: z.string(),
    shift: z.string(),
    attendance_status: z.string(),
    work_mode: z.string().nullish(),
    asset: z.string().nullish(),
    entry_type: z.string().nullish(),
    captured_offline: z.coerce.number().nullish(),
    check_in_time: z.string().nullish(),
    accuracy_m: z.number().nullish(),
    can_review: z.boolean(),
  }),
);
export type PendingT = z.infer<typeof Pending>[number];
/** custom_hr `verifications`: what waits for this engineer's check at a site (Pending Verification). */
export const ToVerify = z.array(
  z.object({
    name: z.string(),
    employee_name: z.string().nullish(),
    attendance_date: z.string(),
    shift: z.string(),
    attendance_status: z.string(),
  }),
);
/** The approval list's shape, so one screen shows both lists (an engineer may verify every entry listed). */
export const asPending = (list: z.infer<typeof ToVerify>): PendingT[] =>
  list.map((v) => ({ ...v, employee: v.employee_name ?? v.name, can_review: true }));
export const EntryDetail = z.object({
  name: z.string(),
  photo: z.string().nullish(),
  remarks: z.string().nullish(),
  captured_at: z.string().nullish(),
  accuracy_m: z.number().nullish(),
});
export const Reviewed = z.array(
  z.object({ name: z.string(), ok: z.boolean(), error: z.string().nullish(), state: z.string().nullish() }),
);

/** "Exceptions only": what deserves a closer look before approving (captured offline, or absent). */
export const isException = (e: PendingT) => !!e.captured_offline || e.attendance_status === 'Absent';
