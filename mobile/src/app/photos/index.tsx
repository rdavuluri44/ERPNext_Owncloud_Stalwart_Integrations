import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { FlatList, ScrollView, View, useWindowDimensions } from 'react-native';

import { useApiRef } from '@/auth/session';
import { OfflineStrip } from '@/components/offline-strip';
import { Thumb } from '@/components/picture';
import { Button, Choice, Status, T } from '@/components/ui';
import { type TextKey, t as text } from '@/i18n';
import { type Place, loadBoot, placesFrom } from '@/lib/attendance';
import { formatDate } from '@/lib/format';
import { KINDS, PAGE, type PhotoT, listPhotos, photoImage } from '@/lib/photos';
import { usePlaceChoice } from '@/lib/places';
import { useTheme } from '@/theme';

const KIND_TEXT: Record<string, TextKey> = { Progress: 'photo.kind.progress', Hindrance: 'photo.kind.hindrance', Incident: 'photo.kind.incident', Other: 'photo.kind.other' };

/**
 * Site photos (P74): the project photos the person may see (ERPNext decides), 30 at a time, 3 per row; filters by
 * site and type. Previews come from Drive's thumbnail service through ERPNext and stay in memory only.
 */
export default function Gallery() {
  const t = useTheme();
  const apiRef = useApiRef();
  const { width } = useWindowDimensions();
  const choice = usePlaceChoice();
  const [places, setPlaces] = useState<Place[]>([]);
  const [site, setSite] = useState<string | null>(choice.site);
  const [kind, setKind] = useState<string | null>(null);
  const [items, setItems] = useState<PhotoT[] | null>(null);
  const [more, setMore] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    (start: number) =>
      listPhotos(apiRef.current, { site: site ?? undefined, kind: kind ?? undefined, start }).then(
        (page) => {
          setItems((old) => (start === 0 ? page : [...(old ?? []), ...page]));
          setMore(page.length === PAGE);
          setError(null);
        },
        (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
      ),
    [apiRef, site, kind],
  );
  useFocusEffect(
    useCallback(() => {
      loadBoot(apiRef.current).then((b) => setPlaces(placesFrom(b)), () => {});
      load(0);
    }, [apiRef, load]),
  );

  const size = Math.floor((width - 16) / 3);
  const siteLabel = (id: string) => places.find((p) => p.site === id)?.siteLabel ?? id;
  const header = (
    <View style={{ padding: 16, gap: 12 }}>
      {error && <Status kind="danger" label={error} />}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
        <Choice label={text('photo.allSites')} selected={!site} onPress={() => setSite(null)} />
        {places.map((p) => (
          <Choice key={p.site} label={p.siteLabel} selected={p.site === site} onPress={() => setSite(p.site)} />
        ))}
      </ScrollView>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
        <Choice label={text('photo.allTypes')} selected={!kind} onPress={() => setKind(null)} />
        {KINDS.map((k) => (
          <Choice key={k} label={text(KIND_TEXT[k])} selected={k === kind} onPress={() => setKind(k)} />
        ))}
      </ScrollView>
      <Button label={text('photo.addTitle')} icon="camera" onPress={() => router.push('/photos/add')} />
      {items && items.length === 0 && <Status kind="none" label={text('photo.none')} />}
      {!items && !error && <Status kind="pending" label={text('myHr.loading')} />}
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: t.c.bg }}>
      <OfflineStrip />
      <FlatList
        data={items ?? []}
        keyExtractor={(p) => p.name}
        numColumns={3}
        ListHeaderComponent={header}
        contentContainerStyle={{ paddingHorizontal: 8, paddingBottom: 24 }}
        onEndReached={() => more && items && items.length > 0 && load(items.length)}
        onEndReachedThreshold={0.5}
        renderItem={({ item }) => (
          <Thumb
            size={size}
            cacheKey={`${item.name}:preview`}
            load={() => photoImage(apiRef.current, item.name, 'preview')}
            label={text('photo.a11y', { kind: text(KIND_TEXT[item.kind] ?? 'photo.kind.other'), site: siteLabel(item.site), date: formatDate(item.taken_at, true) })}
            onPress={() =>
              router.push({
                pathname: '/photos/[name]',
                params: {
                  name: item.name,
                  kind: item.kind,
                  site: siteLabel(item.site),
                  taken: item.taken_at,
                  by: item.taken_by,
                  gallery: item.from_gallery ? '1' : '0',
                  offline: item.captured_offline ? '1' : '0',
                  gps: item.latitude != null && item.longitude != null ? `${item.latitude.toFixed(5)}, ${item.longitude.toFixed(5)} (±${Math.round(item.accuracy_m ?? 0)} m)` : '',
                  remarks: item.remarks ?? '',
                },
              })
            }
          />
        )}
        ListFooterComponent={more && items && items.length > 0 ? <T color="muted" style={{ padding: 16 }}>{text('list.loading')}</T> : undefined}
      />
    </View>
  );
}
