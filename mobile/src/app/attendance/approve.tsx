import { Stack, useLocalSearchParams } from 'expo-router';

import { ApproveView } from '@/components/approve-view';
import { t as text } from '@/i18n';

/** The PM's attendance approval for one site (the view is shared with Today's tablet detail pane). */
export default function Approve() {
  const { site } = useLocalSearchParams<{ site: string }>();
  return (
    <>
      <Stack.Screen options={{ title: text('approve.title') }} />
      <ApproveView site={site} />
    </>
  );
}
