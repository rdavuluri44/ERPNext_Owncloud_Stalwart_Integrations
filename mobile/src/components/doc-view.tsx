import { ActivityIndicator, View } from 'react-native';

import { Button, Status, T } from '@/components/ui';
import { t as text } from '@/i18n';
import { type DocField, type DocMeta, useErp, useMeta } from '@/lib/erp';
import { formatValue, HIDDEN_TYPES } from '@/lib/format';
import { useTheme } from '@/theme';

type Doc = Record<string, unknown> & { name: string; docstatus?: number };

export function docStatus(meta: DocMeta | undefined, doc: Record<string, unknown>) {
  if (doc.docstatus === 2) return { kind: 'danger', label: text('doc.cancelled') } as const;
  if (doc.docstatus === 1) return { kind: 'ok', label: typeof doc.status === 'string' ? doc.status : text('doc.submitted') } as const;
  if (meta?.is_submittable) return { kind: 'warn', label: text('doc.draft') } as const;
  if (typeof doc.status === 'string' && doc.status) return { kind: 'info', label: doc.status } as const;
  return null;
}

const shown = (f: DocField) => !f.hidden && !HIDDEN_TYPES.has(f.fieldtype);

/** Read-only record view built from ERPNext metadata (web parity, v0.1). ERPNext checks permissions. */
export function DocView({ doctype, name }: { doctype: string; name: string }) {
  const t = useTheme();
  const { meta, metas, error: metaError } = useMeta(doctype);
  const { data, error, loading, reload } = useErp<{ data: Doc }>(
    `/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`,
  );
  const doc = data?.data;

  if (error || metaError) {
    return (
      <View style={{ padding: 16, gap: 12 }}>
        <Status kind="danger" label={error ?? metaError ?? text('erp.unexpected')} />
        <Button label={text('inbox.retry')} icon="refresh" secondary onPress={reload} />
      </View>
    );
  }
  if (!doc || !meta) return <ActivityIndicator style={{ margin: 32 }} size="large" color={t.c.primary} />;

  const status = docStatus(meta, doc);
  const rows: React.ReactNode[] = [];
  let heading: string | null = null;
  for (const f of meta.fields) {
    if (f.fieldtype === 'Section Break' || f.fieldtype === 'Tab Break') {
      heading = f.label || null;
      continue;
    }
    if (!shown(f) && f.fieldtype !== 'Table') continue;
    let content: React.ReactNode = null;
    if (f.fieldtype === 'Table') {
      const child = metas.find((m) => m.name === f.options);
      const tableRows = Array.isArray(doc[f.fieldname]) ? (doc[f.fieldname] as Record<string, unknown>[]) : [];
      if (!tableRows.length) continue;
      const cols = (child?.fields ?? []).filter((c) => shown(c) && c.in_list_view).slice(0, 3);
      content = (
        <View style={{ gap: 6 }}>
          {tableRows.map((r, i) => (
            <View key={i} style={{ borderLeftWidth: 3, borderLeftColor: t.c.divider, paddingLeft: 10 }}>
              <T variant="small">
                {`${i + 1}. ${cols.map((c) => formatValue(c, r[c.fieldname])).filter(Boolean).join(' · ') || '—'}`}
              </T>
            </View>
          ))}
        </View>
      );
    } else {
      const text = formatValue(f, doc[f.fieldname]);
      if (!text) continue;
      content = <T selectable>{text}</T>;
    }
    if (heading) {
      rows.push(
        <T key={`h-${f.fieldname}`} variant="title" style={{ marginTop: 12 }}>
          {heading}
        </T>,
      );
      heading = null;
    }
    rows.push(
      <View key={f.fieldname} style={{ gap: 2 }}>
        <T variant="small" color="muted">
          {f.label || f.fieldname}
        </T>
        {content}
      </View>,
    );
  }

  const title = meta.title_field && typeof doc[meta.title_field] === 'string' ? (doc[meta.title_field] as string) : doc.name;
  return (
    <View style={{ padding: 16, gap: 14, opacity: loading ? 0.6 : 1 }}>
      <T variant="title">{title}</T>
      {title !== doc.name && <T color="muted">{doc.name}</T>}
      {status && <Status kind={status.kind} label={status.label} />}
      {rows}
    </View>
  );
}
