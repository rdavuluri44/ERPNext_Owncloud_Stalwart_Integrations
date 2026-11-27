import { View } from 'react-native';

import { Icon } from '@/components/icon';
import { T } from '@/components/ui';
import { t as text } from '@/i18n';
import { formatDate, localToday } from '@/lib/format';
import { useConnection } from '@/lib/saved';
import { useTheme } from '@/theme';

/** "19:36" today, else "22-11-2026 19:36": when the copy on screen was saved. */
export function savedTime(at: number, now = new Date()): string {
  const d = new Date(at);
  const hhmm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  return localToday(d) === localToday(now) ? hhmm : `${formatDate(localToday(d))} ${hhmm}`;
}

/**
 * A slim bar while ERPNext cannot be reached: what is on screen is the copy saved at a given time (or nothing is
 * saved yet), and captures are sent by themselves later. `waiting`: captures in the offline queue.
 */
export function OfflineStrip({ waiting = 0 }: { waiting?: number }) {
  const t = useTheme();
  const { offline, copyFrom } = useConnection();
  if (!offline) return null;
  const parts = [
    copyFrom ? text('offline.copy', { time: savedTime(copyFrom) }) : text('offline.noCopy'),
    waiting > 0 ? text('offline.waiting', { count: waiting }) : null,
  ].filter(Boolean);
  return (
    <View
      accessible
      accessibilityRole="alert"
      accessibilityLabel={`${parts.join('. ')}. ${text('offline.sentLater')}`}
      style={{ flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 16, paddingVertical: 8, backgroundColor: t.c.text }}>
      <Icon name="offline" size={t.font(20)} color={t.c.onPrimary} />
      <T variant="small" style={{ flex: 1, color: t.c.onPrimary, fontWeight: '700' }}>
        {parts.join(' · ')}
      </T>
    </View>
  );
}
