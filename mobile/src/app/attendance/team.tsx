import { Stack, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';

import { TeamView } from '@/components/team-view';
import { t as text } from '@/i18n';

/** The supervisor's team for one site and shift (the view is shared with Today's tablet detail pane). */
export default function TeamScreen() {
  const { site, shift } = useLocalSearchParams<{ site: string; shift: string }>();
  const [title, setTitle] = useState(text('team.title'));
  return (
    <>
      <Stack.Screen options={{ title }} />
      <TeamView site={site} shift={shift} onTitle={setTitle} />
    </>
  );
}
