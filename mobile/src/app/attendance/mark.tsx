import { Stack, router, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ScrollView, View } from 'react-native';
import { z } from 'zod';

import { useApiRef } from '@/auth/session';
import { NoScreenshots } from '@/components/no-screenshots';
import { PhotoTaker } from '@/components/photo-taker';
import { Button, Choice, Status, T, TextArea } from '@/components/ui';
import { t as text } from '@/i18n';
import { OfflineStrip } from '@/components/offline-strip';
import { type BootT, HR_API, loadBoot } from '@/lib/attendance';
import { type Fix, fenceProblem, getFix } from '@/lib/capture';
import { newClientId } from '@/lib/queue';
import { flushQueue, sendOrQueue } from '@/lib/sender';
import { useTheme } from '@/theme';

const Saved = z.object({ name: z.string(), state: z.string().nullish() });

/**
 * Mark one worker for a shift (custom_hr `save_capture`, saved as a draft): Present with a photo of the worker
 * and the location, or Absent with a reason; machine workers are Operating (with a machine of the site) or
 * Standby. The server checks every rule again (assignment, fence, photo, reason, machine, revision).
 */
export default function MarkWorker() {
  const t = useTheme();
  const apiRef = useApiRef();
  const p = useLocalSearchParams<{
    site: string;
    shift: string;
    employee: string;
    workerName: string;
    machine: string;
    entry: string;
    revision: string;
  }>();
  const machine = p.machine === '1';
  const [boot, setBoot] = useState<BootT | null>(null);
  const [status, setStatus] = useState<'Present' | 'Absent'>('Present');
  const [mode, setMode] = useState<'Operating' | 'Standby'>('Operating');
  const [asset, setAsset] = useState<string | null>(null);
  const [remarks, setRemarks] = useState('');
  const [photo, setPhoto] = useState<string | null>(null);
  const [fix, setFix] = useState<Fix | null>(null);
  const [fixError, setFixError] = useState<string | null>(null);
  const [locating, setLocating] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<{ kind: 'ok' | 'pending'; label: string } | null>(null);
  // One request and one capture ID for this screen: a retry returns the same draft (the server compares them).
  const [ids] = useState(() => ({ request: newClientId(), capture: newClientId() }));

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
  useEffect(() => {
    loadBoot(apiRef.current).then(setBoot, (e: unknown) => setError(e instanceof Error ? e.message : String(e)));
    fetchFix().finally(() => setLocating(false));
  }, [apiRef, fetchFix]);

  const site = boot?.sites.find((s) => s.name === p.site);
  const fence = boot?.check_in_sites.find((s) => s.name === p.site) ?? null;
  const problem = fix && fence ? fenceProblem(fix, fence) : null;
  const editing = !!p.entry;
  const missing =
    !fix
      ? null
      : status === 'Present' && !photo && !editing
        ? text('mark.needPhoto')
        : status === 'Absent' && !remarks.trim()
          ? text('mark.needReason')
          : status === 'Present' && machine && mode === 'Operating' && !asset
            ? text('mark.needMachine')
            : null;
  const ready = !!fix && !problem && !missing && !busy && !done;

  const save = async () => {
    if (!ready || !fix) return;
    setBusy(true);
    setError(null);
    const present = status === 'Present';
    const payload = {
      employee: p.employee,
      site: p.site,
      shift: p.shift,
      request_id: ids.request,
      capture_id: ids.capture,
      revision: Number(p.revision || 0),
      attendance_status: status,
      work_mode: present && machine ? mode : 'Not applicable',
      asset: present && machine && mode === 'Operating' ? asset : null,
      remarks: remarks.trim(),
      ...(present && photo ? { photo } : {}),
      ...(editing ? { name: p.entry } : {}),
      ...fix,
    };
    try {
      const res = await sendOrQueue(apiRef.current, `${HR_API}.save_capture`, Saved, payload, ids.capture, new Date());
      setDone('queued' in res ? { kind: 'pending', label: text('mark.queued') } : { kind: 'ok', label: text('mark.saved') });
      flushQueue(apiRef.current).catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e)); // ERPNext's own reason
    } finally {
      setBusy(false);
    }
  };

  return (
    <ScrollView style={{ backgroundColor: t.c.bg }} contentContainerStyle={{ padding: 16, gap: 16 }}>
      <OfflineStrip />
      <Stack.Screen options={{ title: p.workerName }} />
      <NoScreenshots />
      <T variant="title">{p.workerName}</T>
      {error && <Status kind="danger" label={error} />}

      <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
        <Choice label={text('mark.present')} selected={status === 'Present'} onPress={() => setStatus('Present')} />
        <Choice label={text('mark.absent')} selected={status === 'Absent'} onPress={() => setStatus('Absent')} />
      </View>

      {status === 'Present' && machine && (
        <View style={{ gap: 8 }}>
          <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
            <Choice label={text('mark.operating')} selected={mode === 'Operating'} onPress={() => setMode('Operating')} />
            <Choice label={text('mark.standby')} selected={mode === 'Standby'} onPress={() => setMode('Standby')} />
          </View>
          {mode === 'Operating' && (
            <View style={{ gap: 8 }}>
              {(site?.assets ?? []).map((a) => (
                <Choice key={a.name} label={a.label} selected={asset === a.name} onPress={() => setAsset(a.name)} />
              ))}
              {site && site.assets.length === 0 && <Status kind="warn" label={text('mark.noMachines')} />}
            </View>
          )}
        </View>
      )}

      <View style={{ gap: 8 }}>
        {locating && <Status kind="pending" label={text('capture.locating')} />}
        {fix && !locating && <Status kind="ok" label={text('capture.located', { accuracy: Math.round(fix.accuracy_m) })} />}
        {fixError && <Status kind="danger" label={fixError} />}
        {problem && <Status kind="danger" label={problem} />}
        {(fixError || problem) && !locating && (
          <Button
            label={text('capture.locate')}
            icon="locate"
            secondary
            onPress={() => {
              setLocating(true);
              fetchFix().finally(() => setLocating(false));
            }}
          />
        )}
      </View>

      {status === 'Present' && !done && (
        <View style={{ gap: 8 }}>
          <T style={{ fontWeight: '700' }}>{text('mark.photo')}</T>
          <PhotoTaker facing="back" onPhoto={setPhoto} />
        </View>
      )}
      <TextArea
        label={status === 'Absent' ? text('mark.reason') : text('mark.remarks')}
        value={remarks}
        onChange={setRemarks}
      />

      {missing && !done && <Status kind="info" label={missing} />}
      {busy && <Status kind="pending" label={text('checkIn.sending')} />}
      {done && <Status kind={done.kind} label={done.label} />}
      {done ? (
        <Button label={text('mark.back')} icon="back" secondary onPress={() => router.back()} />
      ) : (
        <Button label={text('mark.save')} icon="save" onPress={save} disabled={!ready} />
      )}
    </ScrollView>
  );
}
