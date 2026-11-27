import { useLocalSearchParams } from 'expo-router';
import { ScrollView, View } from 'react-native';

import { useApiRef } from '@/auth/session';
import { FullPicture } from '@/components/picture';
import { Status, T } from '@/components/ui';
import { type TextKey, t as text } from '@/i18n';
import { formatDate } from '@/lib/format';
import { fileImage, photoImage } from '@/lib/photos';
import { useTheme } from '@/theme';

const KIND_TEXT: Record<string, TextKey> = { Progress: 'photo.kind.progress', Hindrance: 'photo.kind.hindrance', Incident: 'photo.kind.incident', Other: 'photo.kind.other' };

/**
 * One photo, full size (fetched when opened, never saved on the phone), with its details. Also shows an image from
 * a project's files (`project` + `path`).
 */
export default function PhotoView() {
  const t = useTheme();
  const apiRef = useApiRef();
  const p = useLocalSearchParams<{
    name: string;
    kind?: string;
    site?: string;
    taken?: string;
    by?: string;
    gallery?: string;
    offline?: string;
    gps?: string;
    remarks?: string;
    project?: string;
    path?: string;
  }>();
  const fromFiles = !!(p.project && p.path);
  const load = () => (fromFiles ? fileImage(apiRef.current, p.project ?? '', p.path ?? '', 'full') : photoImage(apiRef.current, p.name, 'full'));
  const title = fromFiles ? (p.path ?? '').split('/').pop() ?? '' : `${text(KIND_TEXT[p.kind ?? ''] ?? 'photo.kind.other')} · ${p.site ?? ''}`;
  return (
    <ScrollView style={{ backgroundColor: t.c.bg }} contentContainerStyle={{ padding: 16, gap: 12 }}>
      <FullPicture load={load} cacheKey={fromFiles ? `file:${p.project}:${p.path}:full` : `${p.name}:full`} label={title} />
      <View style={{ gap: 4 }}>
        <T variant="title">{title}</T>
        {p.taken ? <T color="muted">{text('photo.takenBy', { date: formatDate(p.taken, true), by: p.by ?? '' })}</T> : null}
        {p.gps ? <T color="muted">{text('photo.gps', { gps: p.gps })}</T> : null}
        {p.remarks ? <T>{p.remarks}</T> : null}
      </View>
      {p.gallery === '1' && <Status kind="info" label={text('photo.markGallery')} />}
      {p.offline === '1' && <Status kind="info" label={text('photo.markOffline')} />}
    </ScrollView>
  );
}
