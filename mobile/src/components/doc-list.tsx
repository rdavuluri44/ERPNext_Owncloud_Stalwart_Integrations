import { useState } from 'react';
import { ActivityIndicator, FlatList, ScrollView, View } from 'react-native';

import { useAuth } from '@/auth/session';
import { DocView, docStatus } from '@/components/doc-view';
import { Button, Row, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { type DocMeta, getJson, useErp, useMeta } from '@/lib/erp';
import { formatValue, HIDDEN_TYPES } from '@/lib/format';
import { useTheme } from '@/theme';

const PAGE = 20;
type Item = Record<string, unknown> & { name: string };

function listQuery(doctype: string, meta: DocMeta, start: number) {
  const fields = [
    'name',
    'docstatus',
    ...(meta.title_field ? [meta.title_field] : []),
    ...(meta.fields.some((f) => f.fieldname === 'status') ? ['status'] : []),
    ...listFields(meta).map((f) => f.fieldname),
  ];
  const q = `fields=${encodeURIComponent(JSON.stringify([...new Set(fields)]))}&order_by=${encodeURIComponent('modified desc')}&limit_page_length=${PAGE}&limit_start=${start}`;
  return `/api/resource/${encodeURIComponent(doctype)}?${q}`;
}

const listFields = (meta: DocMeta) =>
  meta.fields.filter((f) => f.in_list_view && !f.hidden && !HIDDEN_TYPES.has(f.fieldtype) && f.fieldtype !== 'Table').slice(0, 3);

/** One ERPNext list (newest first), 20 at a time. ERPNext returns only records the user may read. */
export function DocList({ doctype, selected, onOpen }: { doctype: string; selected?: string; onOpen: (name: string) => void }) {
  const t = useTheme();
  const { api } = useAuth();
  const { meta, error: metaError } = useMeta(doctype);
  // Settings pages and virtual doctypes are not pageable lists; never ask ERPNext to list them.
  const listable = !!meta && !meta.issingle && !meta.is_virtual;
  const first = useErp<{ data: Item[] }>(listable ? listQuery(doctype, meta, 0) : null);
  const [more, setMore] = useState<Item[]>([]);
  const [moreDone, setMoreDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [moreError, setMoreError] = useState<string | null>(null);

  const items = [...(first.data?.data ?? []), ...more];
  const done = (first.data?.data.length ?? 0) < PAGE || moreDone;
  const error = metaError ?? first.error ?? moreError;

  const loadMore = async () => {
    if (!meta || busy) return;
    setBusy(true);
    setMoreError(null);
    try {
      const res = await getJson<{ data: Item[] }>(api, listQuery(doctype, meta, items.length));
      setMore((old) => [...old, ...res.data]);
      setMoreDone(res.data.length < PAGE);
    } catch (e) {
      setMoreError(e instanceof Error ? e.message : text('erp.unexpected'));
    } finally {
      setBusy(false);
    }
  };

  const refresh = () => {
    setMore([]);
    setMoreDone(false);
    first.reload();
  };

  if (meta?.issingle) return <ScrollView><DocView doctype={doctype} name={doctype} /></ScrollView>;
  if (meta?.is_virtual) {
    return (
      <View style={{ padding: 16 }}>
        <Status kind="info" label={text('list.webOnly')} />
      </View>
    );
  }

  return (
    <FlatList
      data={items}
      keyExtractor={(i) => i.name}
      refreshing={first.loading && items.length > 0}
      onRefresh={refresh}
      renderItem={({ item }) => {
        const titleField = meta?.title_field;
        const title = titleField && typeof item[titleField] === 'string' && item[titleField] ? String(item[titleField]) : item.name;
        const cols = meta ? listFields(meta).map((f) => formatValue(f, item[f.fieldname])) : [];
        const sub = [title !== item.name ? item.name : '', ...cols].filter(Boolean).join(' · ');
        const status = docStatus(meta, item);
        return (
          <Row
            title={title}
            subtitle={[status?.label, sub].filter(Boolean).join(' · ')}
            selected={selected === item.name}
            onPress={() => onOpen(item.name)}
          />
        );
      }}
      ListEmptyComponent={
        error ? (
          <View style={{ padding: 16, gap: 12 }}>
            <Status kind="danger" label={error} />
            <Button label={text('inbox.retry')} icon="refresh" secondary onPress={refresh} />
          </View>
        ) : first.loading || !meta ? (
          <ActivityIndicator style={{ margin: 32 }} size="large" color={t.c.primary} />
        ) : (
          <T color="muted" style={{ padding: 16 }}>
            {text('list.empty')}
          </T>
        )
      }
      ListFooterComponent={
        items.length > 0 ? (
          <View style={{ padding: 16, gap: 12 }}>
            {moreError && <Status kind="danger" label={moreError} />}
            {!done && <Button label={text(busy ? 'list.loading' : 'list.more')} secondary onPress={loadMore} disabled={busy} />}
          </View>
        ) : undefined
      }
    />
  );
}
