import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { ScrollView, View } from 'react-native';

import { useApiRef } from '@/auth/session';
import { OfflineStrip } from '@/components/offline-strip';
import { Choice, Row, Status } from '@/components/ui';
import { t as text } from '@/i18n';
import { type Place, loadBoot, placesFrom, projectsOf } from '@/lib/attendance';
import { formatDate } from '@/lib/format';
import { type FileT, isImage, listFiles } from '@/lib/photos';
import { useTheme } from '@/theme';

const sizeText = (bytes: number) => (bytes >= 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`);

/**
 * Project files (P74): the folders and files of a project's Drive space, read through ERPNext (the person needs a
 * site in that project). Images open in the app; other files open in Drive on a computer for now.
 */
export default function Documents() {
  const t = useTheme();
  const apiRef = useApiRef();
  const params = useLocalSearchParams<{ project?: string; path?: string }>();
  const [places, setPlaces] = useState<Place[]>([]);
  const [project, setProject] = useState<string | null>(params.project ?? null);
  const path = params.path ?? '';
  const [entries, setEntries] = useState<FileT[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      let live = true;
      loadBoot(apiRef.current).then(
        (b) => {
          if (!live) return;
          const list = placesFrom(b);
          setPlaces(list);
          setProject((p) => p ?? projectsOf(list).find((x) => x.project)?.project ?? null);
        },
        (e: unknown) => live && setError(e instanceof Error ? e.message : String(e)),
      );
      return () => {
        live = false;
      };
    }, [apiRef]),
  );
  useFocusEffect(
    useCallback(() => {
      if (!project) return;
      let live = true;
      setEntries(null);
      listFiles(apiRef.current, project, path).then(
        (list) => live && (setEntries(list), setError(null)),
        (e: unknown) => live && setError(e instanceof Error ? e.message : String(e)),
      );
      return () => {
        live = false;
      };
    }, [apiRef, project, path]),
  );

  const projects = projectsOf(places).filter((p) => p.project);
  const open = (e: FileT) => {
    if (e.folder) router.push({ pathname: '/documents', params: { project: project ?? '', path: e.path } });
    else if (isImage(e.path)) router.push({ pathname: '/photos/[name]', params: { name: 'file', project: project ?? '', path: e.path } });
  };

  return (
    <ScrollView style={{ backgroundColor: t.c.bg }}>
      <OfflineStrip />
      <View style={{ padding: 16, gap: 12 }}>
        {error && <Status kind="danger" label={error} />}
        {!path && projects.length > 1 && (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
            {projects.map((p) => (
              <Choice key={p.project} label={p.label || p.project} selected={p.project === project} onPress={() => setProject(p.project)} />
            ))}
          </ScrollView>
        )}
        {path ? <Status kind="info" label={text('docs.folder', { path })} /> : null}
        {places.length > 0 && projects.length === 0 && <Status kind="info" label={text('docs.noProject')} />}
        {project && !entries && !error && <Status kind="pending" label={text('myHr.loading')} />}
        {entries && entries.length === 0 && <Status kind="none" label={text(path ? 'docs.emptyFolder' : 'docs.empty')} />}
      </View>
      {entries?.map((e) => (
        <Row
          key={e.path}
          title={e.name}
          subtitle={
            e.folder
              ? text('docs.isFolder')
              : [sizeText(e.size), e.modified ? formatDate(new Date(e.modified).toISOString().slice(0, 10)) : null, isImage(e.path) ? null : text('docs.webOnly')]
                  .filter(Boolean)
                  .join(' · ')
          }
          onPress={e.folder || isImage(e.path) ? () => open(e) : undefined}
        />
      ))}
      <View style={{ height: 24 }} />
    </ScrollView>
  );
}
