import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';

import { useApiRef } from '@/auth/session';
import { ApproveView } from '@/components/approve-view';
import { HomeHeader } from '@/components/home-header';
import { Icon, type IconName } from '@/components/icon';
import { OfflineStrip } from '@/components/offline-strip';
import { Sheet, SheetOption } from '@/components/sheet';
import { TeamView } from '@/components/team-view';
import { Button, Card, Label, Panel, Progress, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { type TodayAttendance, clock, loadTodayAttendance } from '@/lib/attendance';
import { formatDate, localToday } from '@/lib/format';
import { refreshInbox, useInbox } from '@/lib/inbox';
import { loadTodayHr } from '@/lib/my-hr';
import { offlineStore } from '@/lib/offline-store';
import { loadPlaceChoice, usePlaceChoice } from '@/lib/places';
import { flushQueue } from '@/lib/sender';
import { useIsTablet, useTheme } from '@/theme';

const nowHHMM = (d = new Date()) => `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;

type Hr = Awaited<ReturnType<typeof loadTodayHr>>;
type Action = { key: string; icon: IconName; label: string; go: () => void };

/** What waits for approval, by document type, most first: rows of the design's "Approvals waiting" card. */
function tally(doctypes: string[]): [string, number][] {
  const counts = new Map<string, number>();
  for (const d of doctypes) counts.set(d, (counts.get(d) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

/**
 * Today (owner's reference design, 23 November 2026, to the design brief: 16 pt text, 48 dp targets, 56 dp
 * primary buttons, 7:1 contrast, outlined icons): the header with project, site and shift; my own attendance;
 * then the cards for what the person is at the chosen site, what waits for their approval, and what waits to
 * be sent. Only real data and real actions; the server's role cards (H2) and department modules come later.
 */
export default function Today() {
  const t = useTheme();
  const apiRef = useApiRef();
  const inbox = useInbox();
  const choice = usePlaceChoice();
  const [queue, setQueue] = useState<{ waiting: number; refused: number } | null>(null);
  const [hr, setHr] = useState<Hr>(null);
  const [att, setAtt] = useState<TodayAttendance | null>(null);
  const [sheet, setSheet] = useState(false);

  useEffect(() => {
    loadPlaceChoice();
  }, []);

  const countQueue = useCallback(async () => {
    const items = await (await offlineStore()).all();
    setQueue({
      waiting: items.filter((i) => i.state === 'waiting').length,
      refused: items.filter((i) => i.state === 'failed').length,
    });
  }, []);
  const sendNow = useCallback(async () => {
    await flushQueue(apiRef.current).catch(() => {});
    await countQueue().catch(() => setQueue(null));
  }, [apiRef, countQueue]);

  // Fresh whenever the tab is opened or the place changes: unsent captures go first, then the cards.
  useFocusEffect(
    useCallback(() => {
      let live = true;
      sendNow();
      refreshInbox(apiRef.current);
      loadTodayAttendance(apiRef.current, nowHHMM(), localToday(), choice).then(
        (a) => live && setAtt(a),
        () => live && setAtt(null),
      );
      loadTodayHr(apiRef.current, localToday()).then(
        (h) => live && setHr(h),
        () => live && setHr(null),
      );
      return () => {
        live = false;
      };
    }, [apiRef, sendNow, choice]),
  );

  const unread = inbox.notifications.filter((n) => !n.read).length + inbox.actions.length;
  const site = att?.place;
  const actions: Action[] = [
    ...(att?.self ? [{ key: 'self', icon: 'checked-in' as IconName, label: text('fab.checkIn'), go: () => router.push('/attendance/check-in') }] : []),
    ...(att?.teams ?? []).map((tm) => ({
      key: `team-${tm.siteId}`,
      icon: 'team' as IconName,
      label: text('fab.mark', { site: tm.site }),
      go: () => router.push({ pathname: '/attendance/team', params: { site: tm.siteId, shift: tm.shiftId } }),
    })),
    ...((att?.places.length ?? 0) > 0
      ? [{ key: 'photo', icon: 'camera' as IconName, label: text('fab.photo'), go: () => router.push('/photos/add') }]
      : []),
    ...(att?.checks ?? []).map((c) => ({
      key: `check-${c.siteId}`,
      icon: 'approve' as IconName,
      label: text('fab.verify', { site: c.site }),
      go: () => router.push({ pathname: '/attendance/verify', params: { site: c.siteId } }),
    })),
    ...(att?.approvals ?? []).map((ap) => ({
      key: `appr-${ap.siteId}`,
      icon: 'approve' as IconName,
      label: text('fab.approve', { site: ap.site }),
      go: () => router.push({ pathname: '/attendance/approve', params: { site: ap.siteId } }),
    })),
  ];
  const rows = tally(inbox.actions.map((a) => a.reference_doctype));

  // Tablet (owner's design: split view with a detail inspector): the team or approval opens on the right.
  const tablet = useIsTablet();
  const [detail, setDetail] = useState<{ kind: 'team' | 'approve' | 'verify'; site: string; shift?: string } | null>(null);
  const shown =
    detail ??
    (att?.checks[0]
      ? { kind: 'verify' as const, site: att.checks[0].siteId }
      : att?.approvals[0]
      ? { kind: 'approve' as const, site: att.approvals[0].siteId }
      : att?.teams[0]
        ? { kind: 'team' as const, site: att.teams[0].siteId, shift: att.teams[0].shiftId }
        : null);
  const openTeam = (site: string, shift: string) =>
    tablet ? setDetail({ kind: 'team', site, shift }) : router.push({ pathname: '/attendance/team', params: { site, shift } });
  const openApprove = (site: string) =>
    tablet ? setDetail({ kind: 'approve', site }) : router.push({ pathname: '/attendance/approve', params: { site } });
  const openVerify = (site: string) =>
    tablet ? setDetail({ kind: 'verify', site }) : router.push({ pathname: '/attendance/verify', params: { site } });

  const cards = (
    <>
      {/* My own attendance, a strip under the header (design: "My self-attendance"). */}
      {att?.self && (
        <Pressable
          accessibilityRole="button"
          onPress={() => router.push('/attendance/check-in')}
          style={{
            minHeight: t.touch,
            flexDirection: 'row',
            alignItems: 'center',
            gap: 10,
            paddingHorizontal: 16,
            backgroundColor: att.self.today ? t.c.okTint : t.c.warnTint,
            borderBottomWidth: 1,
            borderBottomColor: t.c.line,
          }}>
          <Icon name={att.self.today ? 'checked-in' : 'not-checked-in'} size={t.font(22)} color={att.self.today ? t.c.ok : t.c.warn} />
          <T style={{ flex: 1, fontWeight: '700' }} color={att.self.today ? 'ok' : 'warn'}>
            {att.self.today
              ? text('today.selfIn', {
                  time: clock(att.self.today.check_in_time),
                  state: att.self.today.state,
                  out: att.self.today.check_out_time ? text('today.checkedOut', { time: clock(att.self.today.check_out_time) }) : '',
                })
              : text('today.selfNotIn')}
          </T>
          <T style={{ fontWeight: '700' }} color="primary">
            {att.self.today ? text('today.details') : text('fab.checkIn')}
          </T>
          <Icon name="chevron-right" size={t.font(20)} color={t.c.primary} />
        </Pressable>
      )}

      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: actions.length ? 104 : 24 }}>
        {/* Supervisor: my team's attendance for the site and shift in the header. */}
        {att?.teams.map((tm) => {
          const left = tm.counts['Not recorded'] ?? 0;
          const sent = ['Submitted', 'Pending Verification', 'Verified', 'Approved'].reduce((n, s) => n + (tm.counts[s] ?? 0), 0);
          return (
            <Panel key={`team-${tm.siteId}`}>
              <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 12 }}>
                <View style={{ flex: 1, gap: 6 }}>
                  <Label text={text('today.shiftLabel', { shift: tm.shift })} />
                  <T variant="title">{text('today.myTeam')}</T>
                </View>
                <View style={{ alignItems: 'flex-end' }}>
                  <T style={{ fontSize: t.font(32), fontWeight: '800' }} color="primary">
                    {`${tm.marked}/${tm.total}`}
                  </T>
                  <T variant="small" color="muted" style={{ fontWeight: '700' }}>
                    {text('today.workers')}
                  </T>
                </View>
              </View>
              <Progress done={tm.marked} total={tm.total} label={text('today.team', { site: tm.site, marked: tm.marked, total: tm.total })} />
              <View style={{ gap: 6, paddingTop: 4 }}>
                {sent > 0 && <Status kind="ok" label={text('today.teamSent', { count: sent })} />}
                {(tm.counts.Draft ?? 0) > 0 && <Status kind="pending" label={text('today.teamDraft', { count: tm.counts.Draft })} />}
                {(tm.counts.Returned ?? 0) > 0 && <Status kind="warn" label={text('today.teamReturned', { count: tm.counts.Returned })} />}
                {left > 0 && <Status kind="warn" label={text('today.teamLeft', { count: left })} />}
                {tm.mine === 0 && <Status kind="info" label={text('today.markedBySupervisors')} />}
              </View>
              <Button
                label={
                  tm.toMark > 0
                    ? text('today.continueMarking', { count: tm.toMark })
                    : tm.drafts > 0
                      ? text('team.submit', { count: tm.drafts })
                      : text('today.openTeam')
                }
                icon={tm.toMark > 0 ? 'camera' : tm.drafts > 0 ? 'fingerprint' : 'team'}
                onPress={() => openTeam(tm.siteId, tm.shiftId)}
              />
            </Panel>
          );
        })}

        {/* Engineer: what their supervisors marked, to check before the PM approves. */}
        {att?.checks.map((c) => (
          <Panel key={`check-${c.siteId}`} accent="primary">
            <Label text={text('today.toCheck')} />
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
              <View style={{ flex: 1, gap: 2 }}>
                <T variant="title">{text('today.checkTitle')}</T>
                <T color="muted">{text('today.checkDetail', { site: c.site })}</T>
              </View>
              <T style={{ fontSize: t.font(32), fontWeight: '800' }}>{c.count}</T>
            </View>
            <Button label={text('today.reviewVerify')} icon="fingerprint" onPress={() => openVerify(c.siteId)} />
          </Panel>
        ))}

        {/* Approver: bulk attendance approval for the site (design: "Fast track action"). */}
        {att?.approvals.map((ap) => (
          <Panel key={`appr-${ap.siteId}`} accent="ok">
            <Label text={text('today.fastTrack')} tone="ok" />
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
              <View style={{ flex: 1, gap: 2 }}>
                <T variant="title">{text('today.bulkApproval')}</T>
                <T color="muted">{text('today.attendanceToApprove', { site: ap.site })}</T>
              </View>
              <T style={{ fontSize: t.font(32), fontWeight: '800' }}>{ap.count}</T>
            </View>
            <View style={{ gap: 6, padding: 10, borderRadius: 10, backgroundColor: t.c.surface }}>
              <Status kind="ok" label={text('today.readyToApprove', { count: ap.reviewable })} />
              {ap.exceptions > 0 && <Status kind="warn" label={text('today.exceptions', { count: ap.exceptions })} />}
            </View>
            <Button
              label={text('today.reviewApprove')}
              icon="fingerprint"
              tone="ok"
              onPress={() => openApprove(ap.siteId)}
            />
          </Panel>
        ))}

        {/* Everyone with workflow approvals: the tally by document type (departments come with H2). */}
        {inbox.loaded && rows.length > 0 && (
          <Panel>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <Icon name="approve" size={t.font(22)} color={t.c.primary} />
              <T style={{ flex: 1, fontWeight: '800' }} color="primary">
                {text('today.waitingForYou').toUpperCase()}
              </T>
              <Label text={text('today.total', { count: inbox.actions.length })} />
            </View>
            {rows.map(([doctype, n], i) => (
              <View
                key={doctype}
                style={{
                  minHeight: 40,
                  flexDirection: 'row',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderTopWidth: i ? 1 : 0,
                  borderTopColor: t.c.surface,
                }}>
                <T style={{ flex: 1 }}>{doctype}</T>
                <T style={{ fontWeight: '800' }}>{text('today.pending', { count: n })}</T>
              </View>
            ))}
            <Button label={text('today.openApprovals')} icon="chevron-right" onPress={() => router.push('/inbox')} />
          </Panel>
        )}
        {inbox.loaded && rows.length === 0 && <Status kind="none" label={text('inbox.noneWaiting')} />}

        {/* Waiting to send: the encrypted offline queue, with "Send now". */}
        {queue && (queue.waiting > 0 || queue.refused > 0) ? (
          <Panel accent="warn">
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
              <Icon name="upload" size={t.font(24)} color={t.c.warn} />
              <View style={{ flex: 1, gap: 2 }}>
                {queue.waiting > 0 && <T style={{ fontWeight: '700' }}>{text('today.captureWaiting', { count: queue.waiting })}</T>}
                <T variant="small" color="muted">
                  {text('today.savedEncrypted')}
                </T>
              </View>
            </View>
            {queue.refused > 0 && <Status kind="danger" label={text('today.refused', { count: queue.refused })} />}
            {queue.waiting > 0 && <Button label={text('today.sendNow')} icon="upload" secondary onPress={sendNow} />}
          </Panel>
        ) : (
          queue && <Status kind="none" label={text('today.nothingWaiting')} />
        )}

        {hr && (hr.nextHoliday || hr.openLeaves > 0) && (
          <Card
            icon="holiday"
            title={
              hr.nextHoliday
                ? text('today.nextHoliday', { date: formatDate(hr.nextHoliday.holiday_date), name: hr.nextHoliday.description ?? '' })
                : text('tab.myHr')
            }
            detail={hr.openLeaves ? text('today.openLeaves', { count: hr.openLeaves }) : undefined}
            onPress={() => router.push('/my-hr')}
          />
        )}
      </ScrollView>
    </>
  );

  return (
    <View style={{ flex: 1, backgroundColor: t.c.page }}>
      <HomeHeader unread={unread} places={att?.places ?? []} place={site ?? null} shift={att?.shift ?? null} />

      <OfflineStrip waiting={queue?.waiting ?? 0} />

      {tablet ? (
        <View style={{ flex: 1, flexDirection: 'row' }}>
          <View style={{ width: 440, borderRightWidth: 1, borderRightColor: t.c.line }}>{cards}</View>
          <View style={{ flex: 1, backgroundColor: t.c.bg }}>
            <View style={{ paddingHorizontal: 16, paddingVertical: 12, gap: 4, borderBottomWidth: 1, borderBottomColor: t.c.line, backgroundColor: t.c.surface }}>
              <Label text={text('today.detail')} />
              <T variant="title">
                {shown ? text(shown.kind === 'approve' ? 'approve.title' : shown.kind === 'verify' ? 'verify.title' : 'today.myTeam') : text('today.detailEmpty')}
              </T>
            </View>
            {shown?.kind === 'approve' && <ApproveView key={`a-${shown.site}`} site={shown.site} />}
            {shown?.kind === 'verify' && <ApproveView key={`v-${shown.site}`} site={shown.site} mode="verify" />}
            {shown?.kind === 'team' && <TeamView key={`t-${shown.site}-${shown.shift}`} site={shown.site} shift={shown.shift ?? ''} />}
          </View>
        </View>
      ) : (
        cards
      )}

      {/* "+" (56 dp+): only the actions this person really has. */}
      {actions.length > 0 && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={text('fab.open')}
          onPress={() => setSheet(true)}
          style={{
            position: 'absolute',
            right: 16,
            bottom: 16,
            width: 64,
            height: 64,
            borderRadius: 32,
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: t.c.primary,
            borderWidth: 3,
            borderColor: t.c.bg,
            elevation: 6,
            shadowColor: '#000',
            shadowOpacity: 0.25,
            shadowRadius: 8,
            shadowOffset: { width: 0, height: 4 },
          }}>
          <Icon name="plus" size={32} color={t.c.onPrimary} />
        </Pressable>
      )}
      <Sheet open={sheet} title={text('fab.title')} onClose={() => setSheet(false)}>
        {actions.map((a) => (
          <SheetOption
            key={a.key}
            icon={a.icon}
            label={a.label}
            onPress={() => {
              setSheet(false);
              a.go();
            }}
          />
        ))}
      </Sheet>
    </View>
  );
}
