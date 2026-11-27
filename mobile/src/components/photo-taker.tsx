import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRef, useState } from 'react';
import { Image, View } from 'react-native';

import { Button, Status } from '@/components/ui';
import { t as text } from '@/i18n';
import { photoDataUrl } from '@/lib/capture';
import { useTheme } from '@/theme';

/**
 * A live camera photo only: no gallery, so an old picture cannot be reused for attendance. `front` for the
 * selfie at self check-in, `back` for the worker a supervisor marks. Gives the shrunk data URL to `onPhoto`.
 */
export function PhotoTaker({ facing, onPhoto }: { facing: 'front' | 'back'; onPhoto: (dataUrl: string | null) => void }) {
  const t = useTheme();
  const [permission, requestPermission] = useCameraPermissions();
  const camera = useRef<CameraView>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!permission) return null;
  if (!permission.granted) {
    return (
      <View style={{ gap: 12 }}>
        <Status kind="warn" label={text('camera.noPermission')} />
        <Button label={text('camera.allow')} icon="camera" secondary onPress={requestPermission} />
      </View>
    );
  }

  const take = async () => {
    if (busy || !camera.current) return;
    setBusy(true);
    setError(null);
    try {
      const shot = await camera.current.takePictureAsync({ quality: 0.7, shutterSound: false });
      const dataUrl = await photoDataUrl(shot.uri); // also deletes the camera's file
      setPreview(dataUrl); // shown from memory, not from a file
      onPhoto(dataUrl);
    } catch (e) {
      setError(e instanceof Error ? e.message : text('capture.photoFailed'));
    } finally {
      setBusy(false);
    }
  };
  const retake = () => {
    setPreview(null);
    onPhoto(null);
  };

  const frame = { width: '100%' as const, aspectRatio: 3 / 4, borderRadius: 12, overflow: 'hidden' as const, borderWidth: t.border, borderColor: t.c.border };
  return (
    <View style={{ gap: 12 }}>
      {preview ? (
        <>
          <Image source={{ uri: preview }} style={frame} accessibilityLabel={text('camera.taken')} />
          <Status kind="ok" label={text('camera.taken')} />
          <Button label={text('camera.retake')} icon="retake" secondary onPress={retake} />
        </>
      ) : (
        <>
          <View style={frame}>
            <CameraView ref={camera} facing={facing} style={{ flex: 1 }} />
          </View>
          {error && <Status kind="danger" label={error} />}
          <Button label={text('camera.take')} icon="camera" onPress={take} disabled={busy} />
        </>
      )}
    </View>
  );
}
