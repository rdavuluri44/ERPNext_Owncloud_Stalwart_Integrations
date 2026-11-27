import Constants from 'expo-constants';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, Switch, TextInput, View } from 'react-native';

import { RELOCK_AFTER_MS } from '@/auth/lock';
import { useApiRef, useAuth } from '@/auth/session';
import { Button, Screen, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { offlineStorageKind, offlineStore } from '@/lib/offline-store';
import { flushQueue } from '@/lib/sender';
import { useTheme } from '@/theme';

const CONFIRM_WORD = 'DELETE';

export default function Settings() {
  const t = useTheme();
  const { user, signOut } = useAuth();
  const apiRef = useApiRef();
  const toggle = () => t.setOutdoor(!t.outdoor);
  const [storage, setStorage] = useState<'encrypted' | 'memory' | null>(null);
  // Owner decision 4 (23 November 2026): with unsent entries, signing out needs "Send now" or the word DELETE.
  const [unsent, setUnsent] = useState(0);
  const [typed, setTyped] = useState('');
  const [sending, setSending] = useState(false);
  const count = useCallback(
    () =>
      offlineStore()
        .then((st) => st.all())
        .then((items) => setUnsent(items.length), () => setUnsent(0)),
    [],
  );
  useEffect(() => {
    offlineStorageKind().then(setStorage, () => setStorage('memory'));
    count();
  }, [count]);
  const sendNow = async () => {
    setSending(true);
    await flushQueue(apiRef.current).catch(() => {});
    await count();
    setSending(false);
  };
  const mayLeave = unsent === 0 || typed.trim() === CONFIRM_WORD;
  return (
    <Screen>
      <View style={{ gap: 6 }}>
        <T variant="title">{user?.name || text('settings.signedIn')}</T>
        {user?.email ? <T color="muted">{user.email}</T> : null}
      </View>

      <Pressable
        accessibilityRole="switch"
        accessibilityState={{ checked: t.outdoor }}
        onPress={toggle}
        style={{
          minHeight: t.touch + 16,
          flexDirection: 'row',
          alignItems: 'center',
          gap: 12,
          padding: 16,
          borderWidth: t.border,
          borderColor: t.c.border,
          borderRadius: 10,
        }}>
        <View style={{ flex: 1, gap: 4 }}>
          <T style={{ fontWeight: '700' }}>{text('settings.outdoor', { state: text(t.outdoor ? 'settings.on' : 'settings.off') })}</T>
          <T variant="small" color="muted">
            {text('settings.outdoorHint')}
          </T>
        </View>
        <Switch
          value={t.outdoor}
          onValueChange={toggle}
          trackColor={{ true: t.c.primary, false: t.c.muted }}
          thumbColor={t.c.bg}
        />
      </Pressable>

      <Status kind="ok" label={text('settings.appLock', { seconds: RELOCK_AFTER_MS / 1000 })} />
      {storage ? (
        <Status
          kind={storage === 'encrypted' ? 'ok' : 'warn'}
          label={text(storage === 'encrypted' ? 'storage.encrypted' : 'storage.memory')}
        />
      ) : null}

      {unsent > 0 && (
        <View style={{ gap: 10 }}>
          <Status kind="warn" label={text('signOut.unsent', { count: unsent })} />
          <Button label={text('today.sendNow')} icon="upload" onPress={sendNow} disabled={sending} />
          <TextInput
            value={typed}
            onChangeText={setTyped}
            accessibilityLabel={text('signOut.typeDelete', { word: CONFIRM_WORD })}
            placeholder={text('signOut.typeDelete', { word: CONFIRM_WORD })}
            placeholderTextColor={t.c.muted}
            autoCapitalize="characters"
            autoCorrect={false}
            style={{
              minHeight: t.touch,
              paddingHorizontal: 12,
              borderWidth: 1,
              borderColor: t.c.line,
              borderRadius: 10,
              color: t.c.text,
              fontSize: t.font(16),
            }}
          />
        </View>
      )}
      <Button label={text('settings.signOut')} icon="sign-out" secondary tone={unsent > 0 ? 'danger' : 'primary'} onPress={signOut} disabled={!mayLeave} />
      <T variant="small" color="muted">
        {text('settings.version', { version: Constants.expoConfig?.version ?? '' })}
      </T>
    </Screen>
  );
}
