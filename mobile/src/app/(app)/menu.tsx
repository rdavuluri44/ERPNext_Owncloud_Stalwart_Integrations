import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, ScrollView, View } from 'react-native';

import { useApiRef } from '@/auth/session';
import { MenuPane } from '@/components/menu-pane';
import { OfflineStrip } from '@/components/offline-strip';
import { Button, Row, SearchField, Status, T } from '@/components/ui';
import { type TextKey, t as text } from '@/i18n';
import { type BootT, loadBoot } from '@/lib/attendance';
import { BOOT_PATH, type Boot, useErp } from '@/lib/erp';
import { useConnection } from '@/lib/saved';
import { searchMenus } from '@/lib/menu-search';
import { useIsTablet, useTheme } from '@/theme';

// ERPNext's own lists, grouped by the app they come from so business work comes first.
// Display only: ERPNext has already decided which menus this user may see.
const GROUPS = ['business', 'office', 'system'] as const;
const GROUP_TEXT: Record<(typeof GROUPS)[number], TextKey> = { business: 'menu.business', office: 'menu.office', system: 'menu.system' };
const WORK_APPS = new Set(['erpnext', 'hrms', 'india_compliance', 'erpnext_drive_integrations', 'razorpayx_integration', 'insights']);
const OFFICE_APPS = new Set<string>();
const groupOf = (app?: string) => (app && WORK_APPS.has(app) ? 'business' : app && OFFICE_APPS.has(app) ? 'office' : 'system');

type Work = { key: string; title: string; subtitle?: string; go: () => void };

/** The app's own functions for this person's roles (custom_hr bootstrap; also offline from its saved copy). */
function workOf(boot: BootT | null): Work[] {
  if (!boot) return [];
  const site = (pathname: '/attendance/team' | '/attendance/verify' | '/attendance/approve', s: string) => () =>
    router.push({ pathname, params: { site: s } });
  return [
    ...(boot.check_in_sites.length
      ? [{ key: 'self', title: text('menu.checkIn'), subtitle: boot.check_in_sites.map((s) => s.label).join(' · '), go: () => router.push('/attendance/check-in') }]
      : []),
    ...boot.sites.filter((s) => s.supervisor).map((s) => ({ key: `t-${s.name}`, title: text('menu.mark'), subtitle: s.label, go: site('/attendance/team', s.name) })),
    ...boot.sites.filter((s) => s.verifier).map((s) => ({ key: `v-${s.name}`, title: text('menu.verify'), subtitle: s.label, go: site('/attendance/verify', s.name) })),
    ...boot.sites.filter((s) => s.approver).map((s) => ({ key: `a-${s.name}`, title: text('menu.approve'), subtitle: s.label, go: site('/attendance/approve', s.name) })),
    ...(boot.sites.length || boot.check_in_sites.length
      ? [
          { key: 'photos', title: text('menu.photos'), subtitle: text('menu.photosHint'), go: () => router.push('/photos') },
          { key: 'photo-add', title: text('menu.addPhoto'), go: () => router.push('/photos/add') },
          { key: 'docs', title: text('menu.documents'), subtitle: text('menu.documentsHint'), go: () => router.push('/documents') },
        ]
      : []),
  ];
}

/**
 * Menu: the person's own work in this app first (by their roles at each site, works offline), then the
 * role-filtered ERPNext lists the person gets on the web desk (online), then Settings.
 */
export default function Menu() {
  const t = useTheme();
  const tablet = useIsTablet();
  const apiRef = useApiRef();
  const [boot, setBoot] = useState<BootT | null>(null);
  useFocusEffect(
    useCallback(() => {
      let live = true;
      loadBoot(apiRef.current).then(
        (b) => live && setBoot(b),
        () => {}, // no attendance module, or offline without a saved copy: no "Your work" rows
      );
      return () => {
        live = false;
      };
    }, [apiRef]),
  );
  const { data, error, loading, reload } = useErp<{ message: Boot }>(BOOT_PATH);
  const menus = data?.message.menus ?? [];
  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const current = selected ?? GROUPS.flatMap((g) => menus.filter((m) => groupOf(m.app) === g))[0]?.name;
  const work = workOf(boot);
  const { offline } = useConnection();

  const heading = (key: TextKey) => (
    <T variant="small" color="muted" style={{ paddingHorizontal: 16, paddingTop: 20, paddingBottom: 6, fontWeight: '700' }}>
      {text(key).toUpperCase()}
    </T>
  );

  const list = (
    <ScrollView style={{ backgroundColor: t.c.bg }} keyboardShouldPersistTaps="handled">
      <OfflineStrip />
      <SearchField value={query} onChange={setQuery} label={text('menu.search')} />
      {query.trim() ? (
        <SearchResults menus={menus} query={query} />
      ) : (
        <>
          {work.length > 0 && (
            <>
              {heading('menu.yourWork')}
              {work.map((w) => (
                <Row key={w.key} title={w.title} subtitle={w.subtitle} onPress={w.go} />
              ))}
            </>
          )}

          {heading('menu.erpLists')}
          {!data && error && (
            <View style={{ paddingHorizontal: 16, paddingBottom: 8, gap: 10 }}>
              <Status kind="info" label={offline ? text('menu.listsOffline') : text('menu.listsUnavailable', { error })} />
              <Button label={text('inbox.retry')} icon="refresh" secondary onPress={reload} />
            </View>
          )}
          {!data && !error && loading && <ActivityIndicator style={{ margin: 16 }} color={t.c.primary} />}
          {data && menus.length === 0 && (
            <View style={{ paddingHorizontal: 16 }}>
              <Status kind="info" label={text('menu.noMenus')} />
            </View>
          )}
          {GROUPS.map((g) => {
            const inGroup = menus.filter((m) => groupOf(m.app) === g);
            if (!inGroup.length) return null;
            return (
              <View key={g}>
                <T color="muted" style={{ paddingHorizontal: 16, paddingTop: 12, paddingBottom: 4, fontWeight: '600' }}>
                  {text(GROUP_TEXT[g])}
                </T>
                {inGroup.map((m) => {
                  const count = m.items.filter((i) => i.type === 'doctype').length;
                  return (
                    <Row
                      key={m.name}
                      title={m.label}
                      subtitle={text(count === 1 ? 'menu.oneList' : 'menu.lists', { count })}
                      selected={tablet && current === m.name}
                      onPress={() => (tablet ? setSelected(m.name) : router.push({ pathname: '/menu/[name]', params: { name: m.name } }))}
                    />
                  );
                })}
              </View>
            );
          })}

          {heading('menu.app')}
          <Row title={text('menu.settings')} subtitle={text('menu.settingsHint')} onPress={() => router.push('/settings')} />
          <View style={{ height: 24 }} />
        </>
      )}
    </ScrollView>
  );

  if (!tablet || !current) return list;
  return (
    <View style={{ flex: 1, flexDirection: 'row', backgroundColor: t.c.bg }}>
      <View style={{ width: 360, borderRightWidth: 1, borderRightColor: t.c.divider }}>{list}</View>
      <ScrollView style={{ flex: 1 }}>
        <MenuPane name={current} />
      </ScrollView>
    </View>
  );
}

/** Lists matching the search across all the person's menus; tap opens the list. */
function SearchResults({ menus, query }: { menus: Boot['menus']; query: string }) {
  const found = searchMenus(menus, query);
  if (!found.length) {
    return (
      <View style={{ paddingHorizontal: 16 }}>
        <Status kind="info" label={text('menu.noMatch', { query: query.trim() })} />
      </View>
    );
  }
  return (
    <View>
      {found.map((f) => (
        <Row
          key={f.doctype}
          title={f.label}
          subtitle={f.menu}
          onPress={() => router.push({ pathname: '/list/[doctype]', params: { doctype: f.doctype } })}
        />
      ))}
    </View>
  );
}
