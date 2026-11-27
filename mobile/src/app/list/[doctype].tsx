import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { ScrollView, View } from 'react-native';

import { DocList } from '@/components/doc-list';
import { DocView } from '@/components/doc-view';
import { T } from '@/components/ui';
import { t as text } from '@/i18n';
import { useIsTablet, useTheme } from '@/theme';

/** Phone: the list; tap opens the record. Tablet: list on the left, record on the right. */
export default function ListScreen() {
  const t = useTheme();
  const tablet = useIsTablet();
  const { doctype } = useLocalSearchParams<{ doctype: string }>();
  const [open, setOpen] = useState<string | null>(null);

  const list = (
    <DocList
      doctype={doctype}
      selected={tablet ? (open ?? undefined) : undefined}
      onOpen={(name) => (tablet ? setOpen(name) : router.push({ pathname: '/doc/[doctype]/[name]', params: { doctype, name } }))}
    />
  );

  return (
    <View style={{ flex: 1, backgroundColor: t.c.bg }}>
      <Stack.Screen options={{ title: doctype }} />
      {tablet ? (
        <View style={{ flex: 1, flexDirection: 'row' }}>
          <View style={{ width: 380, borderRightWidth: 1, borderRightColor: t.c.divider }}>{list}</View>
          <ScrollView style={{ flex: 1 }}>
            {open ? <DocView key={open} doctype={doctype} name={open} /> : (
              <T color="muted" style={{ padding: 16 }}>{text('list.chooseLeft')}</T>
            )}
          </ScrollView>
        </View>
      ) : (
        list
      )}
    </View>
  );
}
