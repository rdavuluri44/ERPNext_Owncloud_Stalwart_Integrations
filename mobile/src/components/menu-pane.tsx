import { router } from 'expo-router';
import { View } from 'react-native';

import { Row, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { BOOT_PATH, type Boot, useErp } from '@/lib/erp';

/** One ERPNext menu (module sidebar): its lists, under their headings. */
export function MenuPane({ name }: { name: string }) {
  const { data } = useErp<{ message: Boot }>(BOOT_PATH);
  const menu = data?.message.menus.find((m) => m.name === name);
  if (!menu) return <View style={{ padding: 16 }}><Status kind="info" label={text('menu.notFound')} /></View>;
  return (
    <View>
      {menu.items.map((item, i) =>
        item.type === 'section' ? (
          <T key={`s${i}`} variant="small" color="muted" style={{ paddingHorizontal: 16, paddingTop: 18, paddingBottom: 6, fontWeight: '700' }}>
            {item.label.toUpperCase()}
          </T>
        ) : (
          <Row
            key={`d${i}`}
            title={item.label}
            onPress={() => router.push({ pathname: '/list/[doctype]', params: { doctype: item.doctype } })}
          />
        ),
      )}
    </View>
  );
}
