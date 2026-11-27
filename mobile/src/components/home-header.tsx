import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { APP_NAME } from '@/auth/session';
import { Icon } from '@/components/icon';
import { Sheet, SheetOption } from '@/components/sheet';
import { T } from '@/components/ui';
import { t as text } from '@/i18n';
import { type Place, type Shift, choosePlace, projectsOf } from '@/lib/places';
import { useTheme } from '@/theme';

/** What the person is at the chosen site, in words ("Approver · Supervisor"), never cut off. */
export function roleBadge(place: Place | null): string {
  if (!place) return '';
  return [
    place.approver && text('role.approver'),
    place.verifier && text('role.verifier'),
    place.supervisor && text('role.supervisor'),
    place.staff && text('role.staff'),
  ]
    .filter(Boolean)
    .join(' · ');
}

const shiftText = (s: Shift) => text('checkIn.shift', { shift: s.label ?? s.name, start: s.start, end: s.end });
const isNight = (s: Shift) => s.start > s.end || /night/i.test(s.label ?? s.name);

/**
 * Today's header (owner's reference design, made compact): app name and the person's role at the chosen site,
 * one-tap Outdoor mode, the Inbox bell with its count; below, one line with the site (and its project) and the
 * shift. 16 pt text, 48 dp targets.
 */
export function HomeHeader({
  unread,
  places,
  place,
  shift,
}: {
  unread: number;
  places: Place[];
  place: Place | null;
  shift: Shift | null;
}) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const [picking, setPicking] = useState(false);
  const appName = APP_NAME || 'ERP';
  const badge = roleBadge(place);
  const night = shift ? isNight(shift) : false;
  const round = {
    width: t.touch,
    height: t.touch,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    borderRadius: t.touch / 2,
  };

  return (
    <View
      style={{
        backgroundColor: t.c.bg,
        borderBottomWidth: 1,
        borderBottomColor: t.c.divider,
        paddingHorizontal: 16,
        paddingTop: insets.top + 8,
        paddingBottom: 8,
        gap: 6,
      }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <View style={{ width: 36, height: 36, borderRadius: 9, backgroundColor: t.c.primary, alignItems: 'center', justifyContent: 'center' }}>
          <T style={{ color: t.c.onPrimary, fontWeight: '800' }}>{appName.slice(0, 1).toUpperCase()}</T>
        </View>
        <View style={{ flex: 1 }}>
          <T style={{ fontWeight: '700' }} numberOfLines={1}>
            {appName}
          </T>
          {badge ? (
            <T variant="small" color="muted" numberOfLines={2}>
              {badge}
            </T>
          ) : null}
        </View>
        <Pressable
          accessibilityRole="switch"
          accessibilityState={{ checked: t.outdoor }}
          accessibilityLabel={text('today.outdoor', { state: t.outdoor ? 'ON' : 'OFF' })}
          onPress={() => t.setOutdoor(!t.outdoor)}
          style={[round, t.outdoor && { backgroundColor: t.c.warnTint }]}>
          <Icon name="sun" size={t.font(24)} color={t.c.warn} />
        </Pressable>
        <Pressable accessibilityRole="button" accessibilityLabel={text('header.inbox', { count: unread })} onPress={() => router.push('/inbox')} style={round}>
          <Icon name="bell" size={t.font(24)} color={t.c.text} />
          {unread > 0 && (
            <View
              style={{
                position: 'absolute',
                top: 4,
                right: 2,
                minWidth: 22,
                height: 22,
                paddingHorizontal: 5,
                borderRadius: 11,
                backgroundColor: t.c.danger,
                alignItems: 'center',
                justifyContent: 'center',
              }}>
              {/* A count badge, not reading text: the bell's spoken label carries the number. */}
              <Text style={{ color: t.c.onPrimary, fontWeight: '800', fontSize: 13 }}>{unread > 99 ? '99+' : String(unread)}</Text>
            </View>
          )}
        </Pressable>
      </View>

      {place && (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          {/* One control for the place: the site and its project (owner: a sub-location is a Field Site of a Project). */}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={text('header.placeA11y', { project: place.projectLabel || text('header.noProject'), site: place.siteLabel })}
            onPress={() => setPicking(true)}
            style={{ flex: 1, minHeight: t.touch, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Icon name="map-pin" size={t.font(20)} color={t.c.primary} />
            <View style={{ flex: 1 }}>
              <T style={{ fontWeight: '700' }} numberOfLines={1}>
                {place.siteLabel}
              </T>
              {place.projectLabel && place.projectLabel !== place.siteLabel ? (
                <T variant="small" color="muted" numberOfLines={1}>
                  {place.projectLabel}
                </T>
              ) : null}
            </View>
            <Icon name="chevron-down" size={t.font(20)} color={t.c.muted} />
          </Pressable>
          {shift && (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={text('header.shiftA11y', { shift: shiftText(shift) })}
              onPress={() => {
                const i = place.shifts.findIndex((s) => s.name === shift.name);
                const next = place.shifts[(i + 1) % place.shifts.length];
                if (next) choosePlace(place.site, next.name);
              }}
              style={{
                minHeight: t.touch,
                flexDirection: 'row',
                alignItems: 'center',
                gap: 6,
                paddingHorizontal: 12,
                borderRadius: t.touch / 2,
                backgroundColor: night ? t.c.infoTint : t.c.warnTint,
              }}>
              <Icon name={night ? 'night' : 'sun'} size={t.font(18)} color={night ? t.c.primary : t.c.warn} />
              <T variant="small" style={{ fontWeight: '700' }} color={night ? 'primary' : 'warn'}>
                {`${shift.start}–${shift.end}`}
              </T>
            </Pressable>
          )}
        </View>
      )}

      <Sheet open={picking} title={text('header.choosePlace')} onClose={() => setPicking(false)}>
        {projectsOf(places).map((p) => (
          <View key={p.project || 'none'} style={{ gap: 8 }}>
            <T variant="small" color="muted" style={{ fontWeight: '700', paddingTop: 4 }}>
              {(p.label || text('header.noProject')).toUpperCase()}
            </T>
            {places
              .filter((x) => x.project === p.project)
              .map((x) => (
                <SheetOption
                  key={x.site}
                  icon="site"
                  label={x.siteLabel}
                  detail={roleBadge(x)}
                  selected={x.site === place?.site}
                  onPress={() => {
                    choosePlace(x.site, null);
                    setPicking(false);
                  }}
                />
              ))}
          </View>
        ))}
      </Sheet>
    </View>
  );
}
