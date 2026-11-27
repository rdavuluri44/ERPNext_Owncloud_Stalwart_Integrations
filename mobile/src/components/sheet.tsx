import type { ReactNode } from 'react';
import { Modal, Pressable, ScrollView, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Icon, type IconName } from '@/components/icon';
import { Button, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { useTheme } from '@/theme';

/** A bottom sheet over a dimmed screen: a title, its content, and a Close button (also tap outside or Back). */
export function Sheet({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <Modal visible={open} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.55)' }} onPress={onClose} accessibilityLabel={text('fab.close')} />
      <View
        style={{
          maxHeight: '80%',
          backgroundColor: t.c.bg,
          padding: 16,
          paddingBottom: 16 + insets.bottom,
          gap: 12,
          borderTopLeftRadius: 20,
          borderTopRightRadius: 20,
        }}>
        <T variant="title">{title}</T>
        <ScrollView contentContainerStyle={{ gap: 10 }}>{children}</ScrollView>
        <Button label={text('fab.close')} icon="close" secondary onPress={onClose} />
      </View>
    </Modal>
  );
}

/** One choice in a sheet: icon, label, optional detail; the chosen one has a check and a thick edge. */
export function SheetOption({
  icon,
  label,
  detail,
  selected,
  onPress,
}: {
  icon: IconName;
  label: string;
  detail?: string;
  selected?: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: !!selected }}
      onPress={onPress}
      style={({ pressed }) => ({
        minHeight: t.touch + 8,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingHorizontal: 14,
        paddingVertical: 10,
        borderRadius: 12,
        borderWidth: selected ? 3 : t.border,
        borderColor: selected ? t.c.primary : t.c.line,
        backgroundColor: pressed ? t.c.surface : t.c.bg,
      })}>
      <Icon name={icon} size={t.font(24)} color={t.c.primary} />
      <View style={{ flex: 1, gap: 2 }}>
        <T style={{ fontWeight: '700' }}>{label}</T>
        {detail ? (
          <T variant="small" color="muted">
            {detail}
          </T>
        ) : null}
      </View>
      {selected && <Icon name="check" size={t.font(24)} color={t.c.primary} label={text('sheet.chosen')} />}
    </Pressable>
  );
}
