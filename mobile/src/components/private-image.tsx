import { useEffect, useState } from 'react';
import { Image } from 'react-native';

import { useApiRef } from '@/auth/session';
import { Status } from '@/components/ui';
import { t as text } from '@/i18n';
import { useTheme } from '@/theme';

/**
 * An ERPNext private file (an attendance photo), fetched as the signed-in person so ERPNext checks their access;
 * kept in memory only while it is on screen, never written to the phone.
 */
export function PrivateImage({ path, label }: { path: string; label: string }) {
  const t = useTheme();
  const apiRef = useApiRef();
  const [uri, setUri] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    apiRef
      .current(path)
      .then(async (res) => {
        if (!res.ok) throw new Error(String(res.status));
        const blob = await res.blob();
        const reader = new FileReader();
        reader.onload = () => live && setUri(String(reader.result));
        reader.onerror = () => live && setFailed(true);
        reader.readAsDataURL(blob);
      })
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [apiRef, path]);

  if (failed) return <Status kind="warn" label={text('approve.noPhoto')} />;
  if (!uri) return <Status kind="pending" label={text('approve.loadingPhoto')} />;
  return (
    <Image
      source={{ uri }}
      accessibilityLabel={label}
      style={{ width: '100%', aspectRatio: 3 / 4, borderRadius: 12, borderWidth: t.border, borderColor: t.c.border }}
    />
  );
}
