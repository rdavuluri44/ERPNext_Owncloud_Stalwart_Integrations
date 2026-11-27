import { Stack, useLocalSearchParams } from 'expo-router';

import { ApproveView } from '@/components/approve-view';
import { t as text } from '@/i18n';

/** The engineer's check of one site's attendance before the PM approves (the view is shared with approval). */
export default function Verify() {
  const { site } = useLocalSearchParams<{ site: string }>();
  return (
    <>
      <Stack.Screen options={{ title: text('verify.title') }} />
      <ApproveView site={site} mode="verify" />
    </>
  );
}
