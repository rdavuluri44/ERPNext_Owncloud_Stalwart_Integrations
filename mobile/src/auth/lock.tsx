// App lock (rule 6/7): Face ID / fingerprint, or the phone passcode, every time the app opens and after
// 60 s in the background. While the app is in the background or app switcher, a blank cover hides data.
// Expo Go cannot use Face ID on iOS, so there it asks for the iPhone passcode instead.
import * as LocalAuthentication from 'expo-local-authentication';
import { useEffect, useRef, useState } from 'react';
import { AppState, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { APP_NAME } from '@/auth/session';
import { Button, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { useTheme } from '@/theme';

export const RELOCK_AFTER_MS = 60_000;

export function AppLock() {
  const t = useTheme();
  const [locked, setLocked] = useState(true);
  const [active, setActive] = useState(AppState.currentState === 'active');
  const [error, setError] = useState<string | null>(null);
  const leftAt = useRef<number | null>(null);
  const busy = useRef(false);

  const unlock = async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      const result = await LocalAuthentication.authenticateAsync({ promptMessage: text('lock.prompt', { app: APP_NAME }) });
      setError(null);
      if (result.success) setLocked(false);
      else if (result.error === 'not_enrolled' || result.error === 'passcode_not_set')
        setError(text('lock.noScreenLock', { app: APP_NAME }));
      else if (result.error !== 'user_cancel' && result.error !== 'app_cancel' && result.error !== 'system_cancel')
        setError(text('lock.failed'));
    } finally {
      busy.current = false;
    }
  };

  useEffect(() => {
    unlock();
    const sub = AppState.addEventListener('change', (state) => {
      setActive(state === 'active');
      if (state === 'background') leftAt.current = Date.now();
      if (state === 'active' && leftAt.current && Date.now() - leftAt.current > RELOCK_AFTER_MS) {
        setLocked(true);
        unlock();
      }
      if (state === 'active') leftAt.current = null;
    });
    return () => sub.remove();
  }, []);

  if (!locked && active) return null;
  return (
    <View style={[StyleSheet.absoluteFill, { backgroundColor: t.c.bg }]}>
      {locked && (
        <SafeAreaView style={{ flex: 1, justifyContent: 'center', padding: 24, gap: 20 }}>
          <T variant="title" style={{ fontSize: t.font(26) }}>
            {text('lock.locked', { app: APP_NAME })}
          </T>
          <Button label={text('lock.unlock')} icon="face" onPress={unlock} />
          {error && <Status kind="warn" label={error} />}
        </SafeAreaView>
      )}
    </View>
  );
}
