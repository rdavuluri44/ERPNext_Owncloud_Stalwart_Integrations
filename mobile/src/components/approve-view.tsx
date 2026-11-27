import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, View } from 'react-native';
import { z } from 'zod';

import { confirmIdentity } from '@/auth/confirm';
import { useApiRef } from '@/auth/session';
import { Icon } from '@/components/icon';
import { NoScreenshots } from '@/components/no-screenshots';
import { OfflineStrip } from '@/components/offline-strip';
import { PrivateImage } from '@/components/private-image';
import { Button, Choice, Status, T, TextArea } from '@/components/ui';
import { type TextKey, t as text } from '@/i18n';
import { EntryDetail, HR_API, Pending, type PendingT, Reviewed, ToVerify, asPending, clock, isException } from '@/lib/attendance';
import { callErp } from '@/lib/erp';
import { callKept, useConnection } from '@/lib/saved';
import { formatDate } from '@/lib/format';
import { useTheme } from '@/theme';

type Detail = z.infer<typeof EntryDetail>;
type Mode = 'approve' | 'verify';
type Result = { name: string; ok: boolean; error?: string | null };

/** The texts that differ between the PM's approval and the engineer's check. */
const TEXTS: Record<Mode, Record<'none' | 'act' | 'confirm' | 'done' | 'needsInternet', TextKey>> = {
  approve: { none: 'approve.none', act: 'approve.approveN', confirm: 'approve.confirmApprove', done: 'approve.approved', needsInternet: 'approve.needsInternet' },
  verify: { none: 'verify.none', act: 'verify.verifyN', confirm: 'verify.confirmVerify', done: 'verify.verified', needsInternet: 'verify.needsInternet' },
};

/**
 * The PM's attendance approval for one site (custom_hr `approvals`): select all or exceptions only, look at an
 * entry's photo, then approve or return the selection with one Face ID (`review_many`, each entry under all the
 * server's rules; the answer says per entry what happened). Nobody approves their own capture or attendance.
 * `mode="verify"`: the engineer's check before the PM (custom_hr `verifications` / `verify`, Verify or Return,
 * one entry per call); the server allows only the assigned engineer.
 */
export function ApproveView({ site, mode = 'approve' }: { site: string; mode?: Mode }) {
  const k = TEXTS[mode];
  const t = useTheme();
  const apiRef = useApiRef();
  const [entries, setEntries] = useState<PendingT[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [onlyExceptions, setOnlyExceptions] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [open, setOpen] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [remarks, setRemarks] = useState('');
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<{ kind: 'ok' | 'danger'; label: string } | null>(null);
  // Offline the list is the saved copy: it can be read, but approving waits for a connection (owner).
  const { offline } = useConnection();

  const load = useCallback(() => {
    setLoading(true);
    (mode === 'verify'
      ? callKept(apiRef.current, `${HR_API}.verifications`, ToVerify, { site }).then(asPending)
      : callKept(apiRef.current, `${HR_API}.approvals`, Pending, { site })
    )
      .then((list) => {
        setEntries(list);
        setSelected(new Set());
        setError(null);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [apiRef, site, mode]);
  useFocusEffect(load);

  const shown = (entries ?? []).filter((e) => !onlyExceptions || isException(e));
  const reviewable = shown.filter((e) => e.can_review);
  const toggle = (name: string) =>
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  const selectAll = () => setSelected(new Set(reviewable.map((e) => e.name)));

  const expand = (name: string) => {
    if (open === name) {
      setOpen(null);
      return;
    }
    setOpen(name);
    setDetail(null);
    callErp(apiRef.current, `${HR_API}.entry`, EntryDetail, { name }).then(setDetail, () => setDetail(null));
  };

  const send = async (names: string[], decision: 'Approve' | 'Return'): Promise<Result[]> => {
    if (mode === 'approve') {
      return callErp(apiRef.current, `${HR_API}.review_many`, Reviewed, { names, decision, remarks: remarks.trim() }, { post: true });
    }
    // No bulk call for the engineer's check: one after another, each answer kept (the server decides each).
    const results: Result[] = [];
    for (const name of names) {
      try {
        await callErp(
          apiRef.current,
          `${HR_API}.verify`,
          z.unknown(),
          { name, decision: decision === 'Approve' ? 'Verify' : 'Return', remarks: remarks.trim() },
          { post: true },
        );
        results.push({ name, ok: true });
      } catch (e) {
        results.push({ name, ok: false, error: e instanceof Error ? e.message : String(e) });
      }
    }
    return results;
  };

  const review = async (decision: 'Approve' | 'Return') => {
    const names = [...selected];
    if (busy || !names.length) return;
    setNote(null);
    if (decision === 'Return' && !remarks.trim()) {
      setNote({ kind: 'danger', label: text('approve.needReason') });
      return;
    }
    const key = decision === 'Approve' ? k.confirm : 'approve.confirmReturn';
    if (!(await confirmIdentity(text(key, { count: names.length })))) {
      setNote({ kind: 'danger', label: text('workflow.notConfirmed') });
      return;
    }
    setBusy(true);
    try {
      const results = await send(names, decision);
      const failed = results.filter((r) => !r.ok);
      setNote(
        failed.length
          ? {
              kind: 'danger',
              label: text('approve.partly', {
                done: results.length - failed.length,
                failed: failed.map((r) => `${nameOf(r.name)}: ${r.error}`).join('; '),
              }),
            }
          : { kind: 'ok', label: text(decision === 'Approve' ? k.done : 'approve.returned', { count: results.length }) },
      );
      setRemarks('');
      load();
    } catch (e) {
      setNote({ kind: 'danger', label: e instanceof Error ? e.message : String(e) });
    } finally {
      setBusy(false);
    }
  };
  const nameOf = (entry: string) => entries?.find((e) => e.name === entry)?.employee_name ?? entry;

  return (
    <ScrollView
      style={{ backgroundColor: t.c.bg }}
      contentContainerStyle={{ padding: 16, gap: 12 }}
      refreshControl={<RefreshControl refreshing={loading && !!entries} onRefresh={load} />}>
      <NoScreenshots />
      <OfflineStrip />
      {error && <Status kind="danger" label={error} />}
      {!entries && !error && <Status kind="pending" label={text('myHr.loading')} />}
      {entries && entries.length === 0 && <Status kind="ok" label={text(k.none)} />}
      {entries && entries.length > 0 && (
        <>
          <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
            <Choice label={text('approve.all')} selected={!onlyExceptions} onPress={() => setOnlyExceptions(false)} />
            <Choice label={text('approve.exceptions')} selected={onlyExceptions} onPress={() => setOnlyExceptions(true)} />
          </View>
          <Button label={text('approve.selectAll', { count: reviewable.length })} icon="box-checked" secondary onPress={selectAll} />
        </>
      )}

      {shown.map((e) => {
        const isSel = selected.has(e.name);
        return (
          <View key={e.name} style={{ borderWidth: isSel ? 4 : t.border, borderColor: isSel ? t.c.primary : t.c.border, borderRadius: 12, padding: 12, gap: 8 }}>
            <Pressable
              accessibilityRole="checkbox"
              accessibilityState={{ checked: isSel, disabled: !e.can_review }}
              disabled={!e.can_review}
              onPress={() => toggle(e.name)}
              style={{ minHeight: t.touch, gap: 4 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                <Icon name={isSel ? 'box-checked' : 'box-empty'} size={t.font(26)} color={e.can_review ? t.c.primary : t.c.muted} />
                <T style={{ flex: 1, fontWeight: '700' }}>{e.employee_name ?? e.employee}</T>
              </View>
              <T variant="small" color="muted">
                {[
                  e.attendance_status,
                  e.entry_type === 'Self' ? text('approve.self') : text('approve.team'),
                  e.check_in_time ? text('approve.at', { time: clock(e.check_in_time) }) : null,
                  e.accuracy_m != null ? text('approve.accuracy', { accuracy: Math.round(e.accuracy_m) }) : null,
                  formatDate(e.attendance_date),
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </T>
            </Pressable>
            {!!e.captured_offline && <Status kind="warn" label={text('approve.offline')} />}
            {!e.can_review && <Status kind="info" label={text('approve.notYours')} />}
            <Button
              label={open === e.name ? text('approve.hide') : text('approve.show')}
              icon={open === e.name ? 'chevron-up' : 'image'}
              secondary
              onPress={() => expand(e.name)}
            />
            {open === e.name && offline && detail?.name !== e.name && <Status kind="info" label={text('approve.photoOffline')} />}
            {open === e.name && detail?.name === e.name && (
              <View style={{ gap: 8 }}>
                {detail.photo ? <PrivateImage path={detail.photo} label={text('approve.photoOf', { name: e.employee_name ?? e.employee })} /> : null}
                {detail.remarks ? <T>{detail.remarks}</T> : null}
              </View>
            )}
          </View>
        );
      })}

      {entries && entries.length > 0 && (
        <View style={{ gap: 12, paddingTop: 8 }}>
          <TextArea label={text('approve.remarks')} value={remarks} onChange={setRemarks} />
          {busy && <Status kind="pending" label={text('checkIn.sending')} />}
          {note && <Status kind={note.kind} label={note.label} />}
          {offline && <Status kind="warn" label={text(k.needsInternet)} />}
          <Button
            label={text(k.act, { count: selected.size })}
            icon="fingerprint"
            onPress={() => review('Approve')}
            disabled={busy || offline || selected.size === 0}
          />
          <Button
            label={text('approve.returnN', { count: selected.size })}
            icon="undo"
            secondary
            onPress={() => review('Return')}
            disabled={busy || offline || selected.size === 0}
          />
        </View>
      )}
    </ScrollView>
  );
}
