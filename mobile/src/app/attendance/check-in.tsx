import { useCallback, useEffect, useState } from 'react';
import { ScrollView, View } from 'react-native';
import { z } from 'zod';

import { useApiRef } from '@/auth/session';
import { NoScreenshots } from '@/components/no-screenshots';
import { PhotoTaker } from '@/components/photo-taker';
import { Button, Choice, Row, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { OfflineStrip } from '@/components/offline-strip';
import { type BootT, type CheckInSiteT, HR_API, Mine, clock, currentShift, loadBoot } from '@/lib/attendance';
import { type Fix, fenceProblem, getFix } from '@/lib/capture';
import { callKept } from '@/lib/saved';
import { localToday } from '@/lib/format';
import { newClientId } from '@/lib/queue';
import { flushQueue, sendOrQueue } from '@/lib/sender';
import { useTheme } from '@/theme';

const nowHHMM = (d = new Date()) => `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
const Result = z.object({ name: z.string(), state: z.string().nullish(), check_in_time: z.string().nullish() });
const OutResult = z.object({ name: z.string(), check_out_time: z.string().nullish() });
type Entry = z.infer<typeof Mine>[number];

/**
 * Own check-in (owner decisions 14-16): a live selfie, a GPS fix inside the site's fence, the server's time
 * (or the corrected phone time when offline). Check-out: inside the fence, no selfie. The server decides.
 */
export default function CheckIn() {
  const t = useTheme();
  const apiRef = useApiRef();
  const [boot, setBoot] = useState<BootT | null>(null);
  const [today, setToday] = useState<Entry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [siteName, setSiteName] = useState<string | null>(null);
  const [shiftName, setShiftName] = useState<string | null>(null);
  const [fix, setFix] = useState<Fix | null>(null);
  const [fixError, setFixError] = useState<string | null>(null);
  const [locating, setLocating] = useState(true); // the first fix starts when the screen opens
  const [photo, setPhoto] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<{ kind: 'ok' | 'pending'; label: string } | null>(null);
  // One client ID per check-in on this screen: a retry (or the offline queue) returns the same entry.
  const [requestId] = useState(newClientId);

  const load = useCallback(async () => {
    try {
      const b = await loadBoot(apiRef.current);
      setBoot(b);
      const mine = await callKept(apiRef.current, `${HR_API}.my_attendance`, Mine);
      setToday(mine.find((m) => m.attendance_date === localToday() && !m.check_out_time) ?? null);
      const first = b.check_in_sites[0];
      if (first) {
        setSiteName((s) => s ?? first.name);
        setShiftName((s) => s ?? currentShift(first.shifts, nowHHMM())?.name ?? null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [apiRef]);

  // State changes only when the GPS answers (never synchronously inside the effect).
  const fetchFix = useCallback(
    () =>
      getFix().then(
        (f) => {
          setFix(f);
          setFixError(null);
        },
        (e: unknown) => setFixError(e instanceof Error ? e.message : String(e)),
      ),
    [],
  );
  const locate = () => {
    setLocating(true);
    fetchFix().finally(() => setLocating(false));
  };

  useEffect(() => {
    load();
    fetchFix().finally(() => setLocating(false));
  }, [load, fetchFix]);

  const site: CheckInSiteT | undefined = boot?.check_in_sites.find((s) => s.name === siteName);
  const problem = fix && site ? fenceProblem(fix, site) : null;
  const checkingOut = !!today;
  const ready = !!site && !!shiftName && !!fix && !problem && (checkingOut || !!photo) && !busy && !done;

  const send = async () => {
    if (!ready || !site || !fix) return;
    setBusy(true);
    setError(null);
    const capturedAt = new Date();
    try {
      if (checkingOut && today) {
        const out = await sendOrQueue(apiRef.current, `${HR_API}.self_check_out`, OutResult, { name: today.name, ...fix }, newClientId(), capturedAt);
        setDone(
          'queued' in out
            ? { kind: 'pending', label: text('checkOut.queued') }
            : { kind: 'ok', label: text('checkOut.done', { time: clock(out.result.check_out_time) }) },
        );
      } else {
        const payload = { site: site.name, shift: shiftName, request_id: requestId, photo, ...fix };
        const res = await sendOrQueue(apiRef.current, `${HR_API}.self_check_in`, Result, payload, requestId, capturedAt);
        setDone(
          'queued' in res
            ? { kind: 'pending', label: text('checkIn.queued') }
            : {
                kind: 'ok',
                label: text(res.result.state === 'Approved' ? 'checkIn.doneApproved' : 'checkIn.done', {
                  time: clock(res.result.check_in_time),
                }),
              },
        );
      }
      flushQueue(apiRef.current).catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e)); // ERPNext's own reason (fence, selfie, already in)
    } finally {
      setBusy(false);
    }
  };

  return (
    <ScrollView style={{ backgroundColor: t.c.bg }} contentContainerStyle={{ padding: 16, gap: 16 }}>
      <OfflineStrip />
      <NoScreenshots />
      {error && <Status kind="danger" label={error} />}
      {boot && boot.check_in_sites.length === 0 && <Status kind="warn" label={text('checkIn.noSites')} />}
      {!boot && !error && <Status kind="pending" label={text('myHr.loading')} />}

      {boot && boot.check_in_sites.length > 1 && (
        <View>
          {boot.check_in_sites.map((s) => (
            <Row key={s.name} title={s.label} selected={s.name === siteName} onPress={() => setSiteName(s.name)} />
          ))}
        </View>
      )}
      {site && (
        <View style={{ gap: 8 }}>
          <T variant="title">{site.label}</T>
          {checkingOut && today ? (
            <Status kind="info" label={text('checkIn.already', { time: clock(today.check_in_time), state: today.state })} />
          ) : (
            <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
              {site.shifts.map((s) => (
                <Choice
                  key={s.name}
                  label={text('checkIn.shift', { shift: s.label ?? s.name, start: s.start, end: s.end })}
                  selected={s.name === shiftName}
                  onPress={() => setShiftName(s.name)}
                />
              ))}
            </View>
          )}
        </View>
      )}

      {site && (
        <View style={{ gap: 8 }}>
          {locating && <Status kind="pending" label={text('capture.locating')} />}
          {fix && !locating && <Status kind="ok" label={text('capture.located', { accuracy: Math.round(fix.accuracy_m) })} />}
          {fixError && <Status kind="danger" label={fixError} />}
          {problem && <Status kind="danger" label={problem} />}
          {(fixError || problem) && !locating && <Button label={text('capture.locate')} icon="locate" secondary onPress={locate} />}
        </View>
      )}

      {site && !checkingOut && !done && (
        <View style={{ gap: 8 }}>
          <T style={{ fontWeight: '700' }}>{text('checkIn.selfie')}</T>
          <PhotoTaker facing="front" onPhoto={setPhoto} />
        </View>
      )}

      {site && !checkingOut && !photo && !done && fix && !problem && <Status kind="info" label={text('checkIn.needSelfie')} />}
      {busy && <Status kind="pending" label={text('checkIn.sending')} />}
      {done && <Status kind={done.kind} label={done.label} />}
      {site && !done && (
        <Button
          label={text(checkingOut ? 'checkOut.send' : 'checkIn.send')}
          icon={checkingOut ? 'sign-out' : 'checked-in'}
          onPress={send}
          disabled={!ready}
        />
      )}
    </ScrollView>
  );
}
