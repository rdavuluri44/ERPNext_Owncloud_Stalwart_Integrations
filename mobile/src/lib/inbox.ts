// Inbox data (build guide section 6): the approvals waiting for the person and their notifications, shared
// by the Inbox screen and the tab's unread badge. ERPNext decides what is listed: Workflow Action rows come
// back only when open and for one of the person's roles (its own permission rule), Notification Logs only
// for the person.
import { useSyncExternalStore } from 'react';
import { z } from 'zod';

import { type Api, callErp } from '@/lib/erp';
import { callKept } from '@/lib/saved';

const Action = z.object({
  name: z.string(),
  reference_doctype: z.string(),
  reference_name: z.string(),
  workflow_state: z.string().nullish(),
  creation: z.string(),
});
const Notification = z.object({
  name: z.string(),
  subject: z.string().nullish(),
  document_type: z.string().nullish(),
  document_name: z.string().nullish(),
  read: z.coerce.number(),
  creation: z.string(),
});
const Logs = z.object({ notification_logs: z.array(Notification) });

export type InboxAction = z.infer<typeof Action>;
export type InboxNotification = z.infer<typeof Notification>;
type State = {
  actions: InboxAction[];
  notifications: InboxNotification[];
  error: string | null;
  loading: boolean;
  loaded: boolean;
};

const EMPTY: State = { actions: [], notifications: [], error: null, loading: false, loaded: false };
let state = EMPTY;
const listeners = new Set<() => void>();
const set = (next: Partial<State>) => {
  state = { ...state, ...next };
  listeners.forEach((l) => l());
};

export const ACTIONS_METHOD = 'frappe.client.get_list';
export const LOGS_METHOD = 'frappe.desk.doctype.notification_log.notification_log.get_notification_logs';
export const MARK_READ_METHOD = 'frappe.desk.doctype.notification_log.notification_log.mark_as_read';

/** Load both lists again; the last good copy stays visible if this fails. */
export async function refreshInbox(api: Api) {
  set({ loading: true });
  try {
    const [actions, logs] = await Promise.all([
      callKept(api, ACTIONS_METHOD, z.array(Action), {
        doctype: 'Workflow Action',
        fields: ['name', 'reference_doctype', 'reference_name', 'workflow_state', 'creation'],
        filters: { status: 'Open' },
        order_by: 'creation desc',
        limit_page_length: 100,
      }),
      callKept(api, LOGS_METHOD, Logs, { limit: 50 }),
    ]);
    set({ actions, notifications: logs.notification_logs, error: null, loading: false, loaded: true });
  } catch (e) {
    set({ error: e instanceof Error ? e.message : String(e), loading: false });
  }
}

/** Mark one notification read on the server and here (the badge updates at once). */
export async function markRead(api: Api, name: string) {
  set({ notifications: state.notifications.map((n) => (n.name === name ? { ...n, read: 1 } : n)) });
  await callErp(api, MARK_READ_METHOD, z.unknown(), { docname: name }, { post: true }).catch(() => {});
}

/** Approvals waiting plus unread notifications: the number on the Inbox tab. */
export const unreadCount = (s: Pick<State, 'actions' | 'notifications'>) =>
  s.actions.length + s.notifications.filter((n) => !n.read).length;

/** Sign-out: nothing from the last person stays in memory. */
export function clearInbox() {
  set(EMPTY);
}

const subscribe = (l: () => void) => {
  listeners.add(l);
  return () => listeners.delete(l);
};

export function useInbox() {
  return useSyncExternalStore(subscribe, () => state);
}

/** "3 Purchase Order · 2 Leave Application": what waits, by document type, most first. */
export function byType(doctypes: string[], top = 3): string {
  const counts = new Map<string, number>();
  for (const d of doctypes) counts.set(d, (counts.get(d) ?? 0) + 1);
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, top)
    .map(([d, n]) => `${n} ${d}`)
    .join(' · ');
}
