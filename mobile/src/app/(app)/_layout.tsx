import { Tabs } from 'expo-router';
import { useEffect } from 'react';
import { AppState } from 'react-native';

import { useApiRef } from '@/auth/session';
import { Icon, type IconName } from '@/components/icon';
import { type TextKey, t as text } from '@/i18n';
import { refreshInbox, unreadCount, useInbox } from '@/lib/inbox';
import { flushQueue } from '@/lib/sender';
import { useSideRail, useTheme } from '@/theme';

/** Owner decision 2: Today · Inbox · My HR · Menu. Phones: bottom tabs; 600 dp and wider: a side rail. */
export default function AppTabs() {
  const t = useTheme();
  const rail = useSideRail();
  const apiRef = useApiRef();
  const waiting = unreadCount(useInbox());
  // The Inbox count is fresh when the app opens and whenever it comes back to the front (no polling).
  useEffect(() => {
    const fresh = () => {
      refreshInbox(apiRef.current);
      flushQueue(apiRef.current).catch(() => {}); // unsent captures go when the app is back in front
    };
    fresh();
    const sub = AppState.addEventListener('change', (s) => s === 'active' && fresh());
    return () => sub.remove();
  }, [apiRef]);
  const tab = (label: TextKey, icon: IconName) => ({
    title: text(label),
    tabBarIcon: ({ focused }: { focused: boolean }) => (
      <Icon name={icon} size={t.font(26)} color={focused ? t.c.primary : t.c.muted} />
    ),
  });
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: t.c.bg },
        headerTintColor: t.c.text,
        headerTitleStyle: { fontSize: t.font(22), fontWeight: '700' },
        tabBarPosition: rail ? 'left' : 'bottom',
        tabBarVariant: rail ? 'material' : 'uikit',
        tabBarActiveTintColor: t.c.primary,
        tabBarInactiveTintColor: t.c.muted,
        // Selected tab gets a shaded block too, so it is not shown by colour alone.
        tabBarActiveBackgroundColor: t.c.surface,
        tabBarLabelStyle: { fontSize: t.font(15), fontWeight: '700' },
        tabBarItemStyle: { minHeight: t.touch },
        tabBarStyle: rail
          ? { backgroundColor: t.c.bg, borderRightWidth: t.border, borderRightColor: t.c.border }
          : { backgroundColor: t.c.bg, borderTopWidth: t.border, borderTopColor: t.c.border },
        sceneStyle: { backgroundColor: t.c.bg },
      }}>
      {/* Today draws its own header (project, site, shift), as in the owner's reference design. */}
      <Tabs.Screen name="index" options={{ ...tab('tab.today', 'today'), headerShown: false }} />
      <Tabs.Screen
        name="inbox"
        options={{
          ...tab('tab.inbox', 'inbox'),
          tabBarBadge: waiting || undefined,
          tabBarBadgeStyle: { backgroundColor: t.c.danger, color: t.c.onPrimary, fontWeight: '700' },
        }}
      />
      <Tabs.Screen name="my-hr" options={tab('tab.myHr', 'person')} />
      <Tabs.Screen name="menu" options={tab('tab.menu', 'menu')} />
    </Tabs>
  );
}
