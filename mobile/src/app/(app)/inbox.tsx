import { router, useFocusEffect } from 'expo-router';
import { useCallback } from 'react';
import { RefreshControl, ScrollView, View } from 'react-native';

import { useApiRef } from '@/auth/session';
import { Button, Row, Status, T } from '@/components/ui';
import { OfflineStrip } from '@/components/offline-strip';
import { t as text } from '@/i18n';
import { formatDate, formatValue } from '@/lib/format';
import { type InboxNotification, markRead, refreshInbox, useInbox } from '@/lib/inbox';
import { useTheme } from '@/theme';

const plain = (html?: string | null) => formatValue({ fieldname: 'subject', fieldtype: 'Text Editor' }, html ?? '');

/** Inbox: approvals waiting for the person (their roles), then their notifications. ERPNext decides both lists. */
export default function Inbox() {
  const t = useTheme();
  const apiRef = useApiRef();
  const inbox = useInbox();

  useFocusEffect(
    useCallback(() => {
      refreshInbox(apiRef.current);
    }, [apiRef]),
  );

  const openNotification = (n: InboxNotification) => {
    if (!n.read) markRead(apiRef.current, n.name);
    if (n.document_type && n.document_name) {
      router.push({ pathname: '/doc/[doctype]/[name]', params: { doctype: n.document_type, name: n.document_name } });
    }
  };

  const heading = (label: string) => (
    <T variant="small" color="muted" style={{ paddingHorizontal: 16, paddingTop: 18, paddingBottom: 6, fontWeight: '700' }}>
      {label.toUpperCase()}
    </T>
  );

  return (
    <ScrollView
      style={{ backgroundColor: t.c.bg }}
      refreshControl={
        <RefreshControl refreshing={inbox.loading && inbox.loaded} onRefresh={() => refreshInbox(apiRef.current)} />
      }>
      <OfflineStrip />
      {inbox.error && (
        <View style={{ padding: 16, gap: 12 }}>
          <Status kind="danger" label={text('inbox.error', { error: inbox.error })} />
          <Button label={text('inbox.retry')} icon="refresh" secondary onPress={() => refreshInbox(apiRef.current)} />
        </View>
      )}
      {!inbox.loaded && !inbox.error && (
        <View style={{ padding: 16 }}>
          <Status kind="pending" label={text('inbox.loading')} />
        </View>
      )}
      {inbox.loaded && (
        <>
          {heading(text('inbox.waiting', { count: inbox.actions.length }))}
          {inbox.actions.length === 0 ? (
            <View style={{ paddingHorizontal: 16 }}>
              <Status kind="none" label={text('inbox.noneWaiting')} />
            </View>
          ) : (
            inbox.actions.map((a) => (
              <Row
                key={a.name}
                title={a.reference_doctype}
                subtitle={[a.reference_name, a.workflow_state, formatDate(a.creation, true)].filter(Boolean).join(' · ')}
                onPress={() =>
                  router.push({
                    pathname: '/doc/[doctype]/[name]',
                    params: { doctype: a.reference_doctype, name: a.reference_name, workflow: '1' },
                  })
                }
              />
            ))
          )}
          {heading(text('inbox.notifications'))}
          {inbox.notifications.length === 0 ? (
            <View style={{ paddingHorizontal: 16 }}>
              <Status kind="none" label={text('inbox.noNotifications')} />
            </View>
          ) : (
            inbox.notifications.map((n) => (
              <Row
                key={n.name}
                title={plain(n.subject) || text('inbox.notification')}
                subtitle={[!n.read && text('inbox.unread'), formatDate(n.creation, true)].filter(Boolean).join(' · ')}
                selected={!n.read}
                onPress={() => openNotification(n)}
              />
            ))
          )}
        </>
      )}
    </ScrollView>
  );
}
