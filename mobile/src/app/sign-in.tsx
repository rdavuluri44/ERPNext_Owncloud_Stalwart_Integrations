import { useState } from 'react';
import { View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { APP_NAME, CLIENT_ID, useAuth } from '@/auth/session';
import { Button, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { useTheme } from '@/theme';

export default function SignIn() {
  const t = useTheme();
  const { signIn } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onPress = async () => {
    setBusy(true);
    setError(null);
    try {
      await signIn();
    } catch (e) {
      setError(e instanceof Error ? e.message : text('signIn.failed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.c.bg }}>
      <View style={{ flex: 1, justifyContent: 'center', padding: 24, gap: 20, maxWidth: 520, width: '100%', alignSelf: 'center' }}>
        <T variant="title" style={{ fontSize: t.font(28) }}>
          {APP_NAME}
        </T>
        <Button label={text(busy ? 'signIn.opening' : 'signIn.button')} icon="fingerprint" onPress={onPress} disabled={busy} />
        <T variant="small" color="muted">
          {text('signIn.hint')}
        </T>
        {!CLIENT_ID && <Status kind="warn" label={text('signIn.notSetUp')} />}
        {error && <Status kind="danger" label={error} />}
      </View>
    </SafeAreaView>
  );
}
