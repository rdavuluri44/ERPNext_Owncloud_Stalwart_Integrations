// My HR (build guide section 6), read only: the person's own HR data from Frappe HR's own app API (the same
// functions its web app uses, hrms.api in Frappe HR 16.60). Frappe HR finds the employee from the signed-in
// user and applies its permissions. Money totals are computed by the server; the app only displays them.
import { z } from 'zod';

import type { StatusKind } from '@/components/ui';
import { type Api, callErp } from '@/lib/erp';

const HR = 'hrms.api';
const money = z.union([z.number(), z.string()]).nullish();

const Employee = z
  .object({
    name: z.string(),
    employee_name: z.string().nullish(),
    designation: z.string().nullish(),
    department: z.string().nullish(),
    company: z.string().nullish(),
  })
  // No active Employee for this sign-in: the function returns None and Frappe then sends {} (no "message").
  .nullish();
const Balances = z.record(
  z.string(),
  z.object({ allocated_leaves: z.number().nullish(), balance_leaves: z.number().nullish() }),
);
const Leaves = z.array(
  z.object({
    name: z.string(),
    leave_type: z.string(),
    from_date: z.string(),
    to_date: z.string(),
    status: z.string().nullish(),
    total_leave_days: z.number().nullish(),
  }),
);
const Claims = z.array(
  z.object({
    name: z.string(),
    posting_date: z.string().nullish(),
    expense_type: z.string().nullish(),
    approval_status: z.string().nullish(),
    status: z.string().nullish(),
    total_claimed_amount: money,
    currency: z.string().nullish(),
  }),
);
const Summary = z.object({
  total_pending_amount: money,
  total_approved_amount: money,
  total_rejected_amount: money,
  currency: z.string().nullish(),
});
const Holidays = z.array(z.object({ holiday_date: z.string(), description: z.string().nullish() }));
const Slips = z.array(
  z.object({
    name: z.string(),
    start_date: z.string().nullish(),
    end_date: z.string().nullish(),
    net_pay: money,
    currency: z.string().nullish(),
  }),
);

export type MyHr = {
  employee: z.infer<typeof Employee>;
  balances: Section<z.infer<typeof Balances>>;
  leaves: Section<z.infer<typeof Leaves>>;
  claims: Section<z.infer<typeof Claims>>;
  summary: Section<z.infer<typeof Summary>>;
  holidays: Section<z.infer<typeof Holidays>>;
  slips: Section<z.infer<typeof Slips>>;
};
/** Each part loads on its own, so one refusal (for example payslips) does not hide the rest. */
export type Section<T> = { data: T } | { error: string };

const section = async <T>(load: Promise<T>): Promise<Section<T>> => {
  try {
    return { data: await load };
  } catch (e) {
    return { error: e instanceof Error ? e.message : String(e) };
  }
};

/** Load My HR. Null when the user is not linked to an active Employee (nothing else to show). */
export async function loadMyHr(api: Api, today: string): Promise<MyHr | null> {
  const employee = await callErp(api, `${HR}.get_current_employee_info`, Employee);
  if (!employee) return null;
  const id = employee.name;
  const [balances, leaves, claims, summary, holidays, slips] = await Promise.all([
    section(callErp(api, `${HR}.get_leave_balance_map`, Balances)),
    section(callErp(api, `${HR}.get_leave_applications`, Leaves, { employee: id, limit: 10 })),
    section(callErp(api, `${HR}.get_expense_claims`, Claims, { employee: id, limit: 10 })),
    section(callErp(api, `${HR}.get_expense_claim_summary`, Summary)),
    section(
      callErp(api, `${HR}.get_holidays_for_employee`, Holidays, { employee: id }).then((all) =>
        all.filter((h) => h.holiday_date >= today).slice(0, 5),
      ),
    ),
    section(
      callErp(api, 'frappe.client.get_list', Slips, {
        doctype: 'Salary Slip',
        fields: ['name', 'start_date', 'end_date', 'net_pay', 'currency'],
        filters: { employee: id, docstatus: 1 },
        order_by: 'start_date desc',
        limit_page_length: 12,
      }),
    ),
  ]);
  return { employee, balances, leaves, claims, summary, holidays, slips };
}

/** Today's HR card: the next holiday and how many leave applications are still open. Null without an employee. */
export async function loadTodayHr(api: Api, today: string) {
  const employee = await callErp(api, `${HR}.get_current_employee_info`, Employee);
  if (!employee) return null;
  const [holidays, leaves] = await Promise.all([
    callErp(api, `${HR}.get_holidays_for_employee`, Holidays, { employee: employee.name }),
    callErp(api, `${HR}.get_leave_applications`, Leaves, { employee: employee.name, limit: 20 }),
  ]);
  return {
    nextHoliday: holidays.find((h) => h.holiday_date >= today) ?? null,
    openLeaves: leaves.filter((l) => l.status === 'Open').length,
  };
}

/** ERPNext's own status word gets a matching icon (shown with the word, never colour alone). */
export function statusKind(status?: string | null): StatusKind {
  if (!status) return 'info';
  if (['Approved', 'Paid', 'Submitted', 'Verified'].includes(status)) return 'ok';
  if (['Rejected', 'Cancelled'].includes(status)) return 'danger';
  return 'pending';
}
