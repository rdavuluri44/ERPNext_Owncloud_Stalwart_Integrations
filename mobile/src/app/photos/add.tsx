import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Image, ScrollView, View } from 'react-native';

import { useApiRef } from '@/auth/session';
import { OfflineStrip } from '@/components/offline-strip';
import { PhotoTaker } from '@/components/photo-taker';
import { Button, Choice, Status, T, TextArea } from '@/components/ui';
import { t as text } from '@/i18n';
import { type Place, loadBoot, placesFrom } from '@/lib/attendance';
import { type Fix, getFix, photoDataUrl } from '@/lib/capture';
import { KINDS, type Kind, PHOTO_API, Uploaded } from '@/lib/photos';
import { usePlaceChoice } from '@/lib/places';
import { newClientId } from '@/lib/queue';
import { flushQueue, sendOrQueue } from '@/lib/sender';
import { useTheme } from '@/theme';

const KIND_TEXT = { Progress: 'photo.kind.progress', Hindrance: 'photo.kind.hindrance', Incident: 'photo.kind.incident', Other: 'photo.kind.other' } as const;

/**
 * Add a site photo (P74): the site (from the header), its type, a camera photo or one from the gallery
 * (marked "From gallery"), the location when there is one, and a remark. It goes to the project's Drive folder
 * through ERPNext, or waits encrypted in the offline queue; no photo file stays on the phone.
 */
export default function AddPhoto() {
  const t = useTheme();
  const apiRef = useApiRef();
  const choice = usePlaceChoice();
  const [places, setPlaces] = useState<Place[] | null>(null);
  const [site, setSite] = useState<string | null>(null);
  const [kind, setKind] = useState<Kind>('Progress');
  const [photo, setPhoto] = useState<string | null>(null);
  const [fromGallery, setFromGallery] = useState(false);
  const [fix, setFix] = useState<Fix | null>(null);
  const [remarks, setRemarks] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ kind: 'ok' | 'pending'; label: string } | null>(null);
  // One phone ID per photo: a retry (or the offline queue) never stores it twice.
  const [clientId, setClientId] = useState(newClientId);

  useEffect(() => {
    loadBoot(apiRef.current).then(
      (b) => {
        const list = placesFrom(b);
        setPlaces(list);
        setSite((s) => s ?? (list.find((p) => p.site === choice.site) ?? list[0])?.site ?? null);
      },
      (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
    );
    // The location is a tag when there is one; a photo without a fix is still saved.
    getFix().then(setFix, () => setFix(null));
  }, [apiRef, choice.site]);

  const fromLibrary = useCallback(async () => {
    setError(null);
    const allowed = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!allowed.granted) {
      setError(text('photo.noGallery'));
      return;
    }
    const picked = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 1, allowsMultipleSelection: false });
    const asset = picked.canceled ? null : picked.assets[0];
    if (!asset) return;
    try {
      setPhoto(await photoDataUrl(asset.uri)); // shrunk in memory; the app's temporary copy is deleted
      setFromGallery(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : text('capture.photoFailed'));
    }
  }, []);

  const save = async () => {
    if (!site || !photo || busy) return;
    setBusy(true);
    setError(null);
    const payload = {
      client_id: clientId,
      site,
      kind,
      photo,
      from_gallery: fromGallery ? 1 : 0,
      remarks: remarks.trim(),
      ...(fix && !fromGallery ? fix : {}),
    };
    try {
      const res = await sendOrQueue(apiRef.current, `${PHOTO_API}.upload_photo`, Uploaded, payload, clientId, new Date());
      setDone('queued' in res ? { kind: 'pending', label: text('photo.queued') } : { kind: 'ok', label: text('photo.saved') });
      flushQueue(apiRef.current).catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e)); // ERPNext's own reason
    } finally {
      setBusy(false);
    }
  };

  const another = () => {
    setPhoto(null);
    setFromGallery(false);
    setRemarks('');
    setDone(null);
    setClientId(newClientId());
  };

  return (
    <ScrollView style={{ backgroundColor: t.c.bg }} contentContainerStyle={{ padding: 16, gap: 16 }}>
      <OfflineStrip />
      {error && <Status kind="danger" label={error} />}
      {!places && !error && <Status kind="pending" label={text('myHr.loading')} />}
      {places && places.length === 0 && <Status kind="info" label={text('photo.noSites')} />}

      {places && places.length > 0 && !done && (
        <>
          <View style={{ gap: 8 }}>
            <T style={{ fontWeight: '700' }}>{text('photo.site')}</T>
            <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
              {places.map((p) => (
                <Choice key={p.site} label={p.siteLabel} selected={p.site === site} onPress={() => setSite(p.site)} />
              ))}
            </View>
          </View>
          <View style={{ gap: 8 }}>
            <T style={{ fontWeight: '700' }}>{text('photo.type')}</T>
            <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
              {KINDS.map((k) => (
                <Choice key={k} label={text(KIND_TEXT[k])} selected={k === kind} onPress={() => setKind(k)} />
              ))}
            </View>
          </View>

          {photo && fromGallery ? (
            <View style={{ gap: 8 }}>
              <Image source={{ uri: photo }} accessibilityLabel={text('photo.chosen')} style={{ width: '100%', aspectRatio: 3 / 4, borderRadius: 12 }} />
              <Status kind="info" label={text('photo.fromGallery')} />
              <Button label={text('photo.change')} icon="image" secondary onPress={fromLibrary} />
            </View>
          ) : (
            <View style={{ gap: 8 }}>
              <PhotoTaker
                facing="back"
                onPhoto={(p) => {
                  setPhoto(p);
                  setFromGallery(false);
                }}
              />
              {!photo && <Button label={text('photo.gallery')} icon="image" secondary onPress={fromLibrary} />}
            </View>
          )}
          {!fromGallery && <Status kind={fix ? 'ok' : 'info'} label={fix ? text('capture.located', { accuracy: Math.round(fix.accuracy_m) }) : text('photo.noLocation')} />}
          <TextArea label={text('photo.remarks')} value={remarks} onChange={setRemarks} />
          {busy && <Status kind="pending" label={text('checkIn.sending')} />}
          <Button label={text('photo.save')} icon="upload" onPress={save} disabled={!photo || !site || busy} />
        </>
      )}

      {done && (
        <View style={{ gap: 12 }}>
          <Status kind={done.kind} label={done.label} />
          <Button label={text('photo.another')} icon="camera" onPress={another} />
          <Button label={text('mark.back')} icon="back" secondary onPress={() => router.back()} />
        </View>
      )}
    </ScrollView>
  );
}
