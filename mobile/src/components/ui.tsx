import type { ReactNode } from 'react';
import { Pressable, ScrollView, Text, TextInput, View, type TextProps } from 'react-native';

import { Icon, type IconName } from '@/components/icon';
import { t as text } from '@/i18n';
import type { PaletteColor } from '@/theme/colors';
import { useTheme } from '@/theme';

export type { IconName } from '@/components/icon';

// Owner's minimum is 16 pt; hierarchy comes from weight and colour (titles 20 pt, secondary text in `muted`).
const SIZES = { small: 16, body: 16, title: 20 } as const;

/** Text. Minimum 16 pt so it stays readable in sunlight; bolder in Outdoor mode. */
export function T({
  variant = 'body',
  color = 'text',
  style,
  ...rest
}: TextProps & { variant?: keyof typeof SIZES; color?: PaletteColor }) {
  const t = useTheme();
  return (
    <Text
      {...rest}
      style={[
        {
          color: t.c[color],
          fontSize: t.font(SIZES[variant]),
          fontWeight: variant === 'title' || t.outdoor ? '700' : '400',
        },
        style,
      ]}
    />
  );
}

/** A labelled text box (several lines), large text and a visible border. */
export function TextArea({ label, value, onChange }: { label: string; value: string; onChange: (text: string) => void }) {
  const t = useTheme();
  return (
    <View style={{ gap: 6 }}>
      <T style={{ fontWeight: '700' }}>{label}</T>
      <TextInput
        value={value}
        onChangeText={onChange}
        accessibilityLabel={label}
        multiline
        style={{
          minHeight: t.touch * 2,
          padding: 12,
          borderWidth: t.border,
          borderColor: t.c.border,
          borderRadius: 10,
          color: t.c.text,
          fontSize: t.font(16),
          textAlignVertical: 'top',
        }}
      />
    </View>
  );
}

/** One choice of several (Present / Absent, Operating / Standby): selected is shown by a tick and a thick border. */
export function Choice({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={{
        minHeight: t.touch,
        justifyContent: 'center',
        paddingHorizontal: 12,
        borderRadius: 10,
        borderWidth: selected ? t.border + 2 : t.border,
        borderColor: selected ? t.c.primary : t.c.border,
        backgroundColor: selected ? t.c.infoTint : t.c.bg,
      }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        {selected && <Icon name="check" size={t.font(22)} color={t.c.primary} />}
        <T style={{ fontWeight: selected ? '700' : '400' }} color={selected ? 'primary' : 'text'}>
          {label}
        </T>
      </View>
    </Pressable>
  );
}

/** A search box: large text, a 48 dp+ target, a visible border (not colour alone) and a clear button. */
export function SearchField({
  value,
  onChange,
  label,
}: {
  value: string;
  onChange: (text: string) => void;
  label: string;
}) {
  const t = useTheme();
  return (
    <View
      style={{
        minHeight: t.touch,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        margin: 16,
        paddingHorizontal: 12,
        borderWidth: t.border,
        borderColor: t.c.border,
        borderRadius: 10,
        backgroundColor: t.c.bg,
      }}>
      <Icon name="search" size={t.font(24)} color={t.c.text} />
      <TextInput
        value={value}
        onChangeText={onChange}
        placeholder={label}
        placeholderTextColor={t.c.muted}
        accessibilityLabel={label}
        autoCorrect={false}
        autoCapitalize="none"
        returnKeyType="search"
        style={{ flex: 1, minHeight: t.touch, color: t.c.text, fontSize: t.font(16) }}
      />
      {value ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={text('search.clear')}
          onPress={() => onChange('')}
          hitSlop={12}
          style={{ minWidth: t.touch, minHeight: t.touch, alignItems: 'center', justifyContent: 'center' }}>
          <Icon name="clear" size={t.font(24)} color={t.c.text} />
        </Pressable>
      ) : null}
    </View>
  );
}

export function Button({
  label,
  onPress,
  icon,
  secondary,
  disabled,
  tone = 'primary',
}: {
  label: string;
  onPress: () => void;
  icon?: IconName;
  secondary?: boolean;
  /** Filled colour: primary (blue), ok (green, approve), danger (red, return). */
  tone?: 'primary' | 'ok' | 'danger';
  /** While an action is being sent: the button cannot be pressed again. */
  disabled?: boolean;
}) {
  const t = useTheme();
  const fill = t.c[tone];
  const fg = secondary ? fill : t.c.onPrimary;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!disabled }}
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => ({
        minHeight: t.touch + 8,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        paddingHorizontal: 20,
        borderRadius: 10,
        borderWidth: secondary ? Math.max(t.border, 1.5) : 0,
        borderColor: fill,
        backgroundColor: secondary ? t.c.bg : fill,
        opacity: pressed && !disabled ? 0.75 : 1, // no dimming: text keeps its 7:1 contrast
      })}>
      {icon && <Icon name={icon} size={t.font(22)} color={fg} />}
      <Text style={{ color: fg, fontSize: t.font(16), fontWeight: '700' }}>{label}</Text>
    </Pressable>
  );
}

// Status is always icon + text, never colour alone (rule 13).
const STATUS = {
  ok: { icon: 'ok', color: 'ok' },
  warn: { icon: 'warn', color: 'warn' },
  danger: { icon: 'danger', color: 'danger' },
  info: { icon: 'info', color: 'primary' },
  pending: { icon: 'pending', color: 'primary' },
  offline: { icon: 'offline', color: 'muted' },
  none: { icon: 'ok', color: 'muted' },
} as const satisfies Record<string, { icon: IconName; color: PaletteColor }>;

export type StatusKind = keyof typeof STATUS;

export function Status({ kind, label }: { kind: StatusKind; label: string }) {
  const t = useTheme();
  const s = STATUS[kind];
  return (
    <View
      accessible
      accessibilityLabel={label}
      // A status line, not a box: icon and words (the colour is never the only signal).
      style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 8, paddingVertical: 2 }}>
      <Icon name={s.icon} size={t.font(20)} color={t.c[s.color]} />
      <T variant="small" color={s.color} style={{ flex: 1, fontWeight: '600' }}>
        {label}
      </T>
    </View>
  );
}

/** A white card on the grey page (owner's reference design); `accent` adds a coloured left edge. */
export function Panel({ accent, children }: { accent?: 'primary' | 'ok' | 'warn' | 'danger'; children: ReactNode }) {
  const t = useTheme();
  return (
    <View
      style={{
        gap: 10,
        padding: 16,
        borderRadius: 14,
        backgroundColor: t.c.bg,
        borderWidth: 1,
        borderColor: t.c.divider,
        borderLeftWidth: accent ? 5 : 1,
        borderLeftColor: accent ? t.c[accent] : t.c.divider,
      }}>
      {children}
    </View>
  );
}

/** A small label in capitals on a tinted strip, as the design's card headings. */
export function Label({ text: label, tone = 'primary' }: { text: string; tone?: 'primary' | 'ok' | 'warn' | 'danger' }) {
  const t = useTheme();
  const tint = { primary: t.c.infoTint, ok: t.c.okTint, warn: t.c.warnTint, danger: t.c.dangerTint }[tone];
  return (
    <View style={{ alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6, backgroundColor: tint }}>
      <T variant="small" color={tone} style={{ fontWeight: '700', letterSpacing: 0.4 }}>
        {label.toUpperCase()}
      </T>
    </View>
  );
}

/** A progress bar (always shown with its numbers in words next to it; never the only information). */
export function Progress({ done, total, label }: { done: number; total: number; label: string }) {
  const t = useTheme();
  const share = total > 0 ? Math.min(1, done / total) : 0;
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityLabel={label}
      accessibilityValue={{ min: 0, max: total, now: done }}
      style={{ height: 10, borderRadius: 5, backgroundColor: t.c.surface, borderWidth: t.outdoor ? 1 : 0, borderColor: t.c.border, overflow: 'hidden' }}>
      <View style={{ width: `${share * 100}%`, height: '100%', backgroundColor: t.c.primary }} />
    </View>
  );
}

/** A Today card: icon, title and detail in words, an optional count, tappable when it leads somewhere. */
export function Card({
  icon,
  title,
  detail,
  count,
  onPress,
}: {
  icon: IconName;
  title: string;
  detail?: string;
  count?: number;
  onPress?: () => void;
}) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole={onPress ? 'button' : undefined}
      accessibilityLabel={[title, detail].filter(Boolean).join('. ')}
      onPress={onPress}
      disabled={!onPress}
      style={({ pressed }) => ({
        minHeight: t.touch + 24,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 14,
        padding: 16,
        borderWidth: 1,
        borderColor: t.c.divider,
        borderRadius: 14,
        backgroundColor: pressed ? t.c.surface : t.c.bg,
      })}>
      <Icon name={icon} size={t.font(26)} color={t.c.primary} />
      <View style={{ flex: 1, gap: 4 }}>
        <T style={{ fontWeight: '700' }}>{title}</T>
        {detail ? (
          <T variant="small" color="muted">
            {detail}
          </T>
        ) : null}
      </View>
      {count !== undefined && (
        <T variant="title" style={{ minWidth: 32, textAlign: 'right' }}>
          {count}
        </T>
      )}
      {onPress && <Icon name="chevron-right" size={t.font(24)} color={t.c.text} />}
    </Pressable>
  );
}

/** A tappable list row; `selected` (tablet split view) adds a thick left bar, not just a colour change. */
export function Row({
  title,
  subtitle,
  onPress,
  selected,
  children,
}: {
  title: string;
  subtitle?: string;
  onPress?: () => void;
  selected?: boolean;
  /** Status lines of this row, shown under the title inside the row. */
  children?: ReactNode;
}) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      disabled={!onPress}
      style={({ pressed }) => ({
        minHeight: t.touch + 16,
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderBottomWidth: 1,
        borderBottomColor: t.c.divider,
        borderLeftWidth: selected ? 5 : 0,
        borderLeftColor: t.c.primary,
        backgroundColor: selected || pressed ? t.c.surface : t.c.bg,
      })}>
      <View style={{ flex: 1, gap: 2 }}>
        <T style={{ fontWeight: '600' }}>{title}</T>
        {subtitle ? (
          <T variant="small" color="muted">
            {subtitle}
          </T>
        ) : null}
        {children ? <View style={{ gap: 2, paddingTop: 4 }}>{children}</View> : null}
      </View>
      {onPress && <Icon name="chevron-right" size={t.font(22)} color={t.c.muted} />}
    </Pressable>
  );
}

export function Screen({ children }: { children: ReactNode }) {
  const t = useTheme();
  return (
    <ScrollView style={{ backgroundColor: t.c.bg }} contentContainerStyle={{ padding: 16, gap: 16 }}>
      {children}
    </ScrollView>
  );
}
