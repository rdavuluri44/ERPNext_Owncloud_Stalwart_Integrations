import { useEffect, useState } from 'react';
import { Image, Pressable, ScrollView, View, useWindowDimensions } from 'react-native';

import { Icon } from '@/components/icon';
import { Status } from '@/components/ui';
import { t as text } from '@/i18n';
import { useTheme } from '@/theme';

/** Loads a picture (a data URL from ERPNext) once; `null` while loading, `false` when it failed. */
function usePicture(load: () => Promise<string>, key: string) {
  const [picture, setPicture] = useState<{ key: string; uri: string | false } | null>(null);
  useEffect(() => {
    let live = true;
    load().then(
      (uri) => live && setPicture({ key, uri }),
      () => live && setPicture({ key, uri: false }),
    );
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `key` names what `load` fetches
  }, [key]);
  return picture?.key === key ? picture.uri : null;
}

/** A square preview tile; tap opens it. A grey square with an icon while loading or without signal. */
export function Thumb({ load, cacheKey, label, size, onPress }: { load: () => Promise<string>; cacheKey: string; label: string; size: number; onPress: () => void }) {
  const t = useTheme();
  const uri = usePicture(load, cacheKey);
  return (
    <Pressable accessibilityRole="imagebutton" accessibilityLabel={label} onPress={onPress} style={{ width: size, height: size, padding: 2 }}>
      {uri ? (
        <Image source={{ uri }} style={{ flex: 1, borderRadius: 6 }} />
      ) : (
        <View style={{ flex: 1, borderRadius: 6, backgroundColor: t.c.surface, alignItems: 'center', justifyContent: 'center' }}>
          <Icon name={uri === false ? 'offline' : 'image'} size={24} color={t.c.muted} />
        </View>
      )}
    </Pressable>
  );
}

/** The full picture, fitted to the screen; tap to zoom in (then drag to look around) and tap again to fit. */
export function FullPicture({ load, cacheKey, label }: { load: () => Promise<string>; cacheKey: string; label: string }) {
  const { width } = useWindowDimensions();
  const uri = usePicture(load, cacheKey);
  const [zoomed, setZoomed] = useState(false);
  if (uri === false) return <Status kind="warn" label={text('photo.notLoaded')} />;
  if (!uri) return <Status kind="pending" label={text('approve.loadingPhoto')} />;
  const w = zoomed ? width * 2.5 : width - 32;
  return (
    <ScrollView horizontal={zoomed} scrollEnabled={zoomed} contentContainerStyle={{ alignItems: 'flex-start' }}>
      <ScrollView scrollEnabled={zoomed} nestedScrollEnabled>
        <Pressable accessibilityRole="button" accessibilityLabel={`${label}. ${text(zoomed ? 'photo.fit' : 'photo.zoom')}`} onPress={() => setZoomed((z) => !z)}>
          <Image source={{ uri }} accessibilityLabel={label} resizeMode="contain" style={{ width: w, height: w * (4 / 3), borderRadius: zoomed ? 0 : 12 }} />
        </Pressable>
      </ScrollView>
    </ScrollView>
  );
}
