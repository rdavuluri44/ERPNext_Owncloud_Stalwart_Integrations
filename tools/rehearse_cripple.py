#!/usr/bin/env python3
"""Rehearse the crippled export on a TEST host, against copies of its own data.

Reads the test site's databases and files into a private scratch folder, runs
the same `cripple()` used by the production exporter, then audits the result:
identifiers seen in the originals (e-mail addresses, Indian mobile numbers, PAN,
GSTIN) that survive are counted per table, and Drive is checked for surviving
file names. Prints counts only, never values. Live test data is not changed;
the scratch folder is removed at the end.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from cripple_snapshot import cripple, unpack
from export_snapshot import inspect, mount, safe_copy, business_counts, sql_dump

TOKENS = re.compile(rb'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]+|(?<![0-9])[6-9][0-9]{9}(?![0-9])|'
                    rb'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]|(?<![A-Z])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z])')
TABLE = re.compile(rb'^INSERT INTO [`"]?([^`" ]+)[`"]?|^COPY (?:public\.)?([a-z_]+)')


def masked(token):
    text = token.decode(errors='replace')
    if '@' in text:
        local, _, domain = text.partition('@')
        return local[:1] + '***@' + domain
    return text[:2] + '***' + text[-2:]


def tokens_by_table(path):
    found = {}
    current = b'?'
    with open(path, 'rb') as stream:
        for line in stream:
            match = TABLE.match(line)
            if match:
                current = match.group(1) or match.group(2)
            for token in TOKENS.findall(line):
                found.setdefault(token.lower(), set()).add(current.decode(errors='replace'))
    return found


def drive_names(root, kinds=None):
    names = set()
    for file in Path(root).rglob('*.mpk'):
        if file.is_symlink():
            continue
        try:
            value = unpack(file.read_bytes()).get('user.ocis.name')
        except ValueError:
            continue
        if value and len(value) > 3:
            names.add(value)
            if kinds is not None:
                kinds.setdefault(value, set()).add((unpack(file.read_bytes()).get('user.ocis.type') or b'?').decode())
    return names


PUBLIC_MAIL_PROVIDERS = ('gmail', 'yahoo', 'outlook', 'hotmail')


def audit_domains(config):
    """Mail domain names whose addresses must not survive scrambling: the public providers, the deployment's own
    domains and those listed in the private worker profile (`audit_mail_domains`, for example a client's). Client
    names never live in this repository (P84). Each domain counts by its name part (`name.tld` -> `name`)."""
    labels = list(PUBLIC_MAIL_PROVIDERS)
    for value in [config.get('domain'), config.get('mail_domain')] + list(config.get('audit_mail_domains') or []):
        parts = [p for p in str(value or '').lower().strip('.').split('.') if p]
        label = parts[-2] if len(parts) >= 2 else (parts[0] if parts else '')
        if re.fullmatch(r'[a-z0-9-]+', label) and label not in labels and label != 'example':
            labels.append(label)
    return labels


def column_audit(container, database, found, domains=PUBLIC_MAIL_PROVIDERS):
    """Count rows still holding a real-looking e-mail address, per table.column (no values)."""
    from cripple_snapshot import mysql_rows, sql_literal, quote, TEXTUAL
    rows = mysql_rows(container, database, 'SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS '
                      f'WHERE TABLE_SCHEMA={sql_literal(database)}')
    for table_name, column, data_type in rows:
        if data_type not in TEXTUAL or table_name.startswith('_cripple'):
            continue
        count = mysql_rows(container, database, f'SELECT COUNT(*) FROM {quote(table_name)} WHERE {quote(column)} REGEXP '
                           "'[A-Za-z0-9._%+-]+@(" + '|'.join(domains) + ")[.]'")[0][0]
        if count != '0':
            found[table_name + '.' + column] = int(count)


def names_audit(container, database, names, found, keep_sql="'administrator','guest'"):
    """Count rows per table.column still containing a real person's name (names of accounts that are
    not kept). Counts only, never values."""
    from cripple_snapshot import mysql_rows, sql_literal, quote, TEXTUAL, SWEEP_SKIP_TABLES
    rows = mysql_rows(container, database, 'SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS '
                      f'WHERE TABLE_SCHEMA={sql_literal(database)}')
    if not names:
        return
    condition = ' OR '.join('{col} LIKE ' + sql_literal('%' + n.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%')
                            for n in names)
    for table_name, column, data_type in rows:
        if data_type not in TEXTUAL or table_name.startswith('_cripple') or table_name[3:] in SWEEP_SKIP_TABLES \
                or table_name == 'tabScheduled Job Type':
            continue
        extra = f' AND LOWER(name) NOT IN ({keep_sql})' if table_name == 'tabUser' else ''  # kept identity stays real
        count = mysql_rows(container, database, f'SELECT COUNT(*) FROM {quote(table_name)} WHERE ('
                           + condition.replace('{col}', quote(column)) + ')' + extra)[0][0]
        if count != '0':
            found[table_name + '.' + column] = int(count)


def rehearse(config, keep_accounts, days):
    containers = config['containers']
    backend = inspect(containers['erp_backend'])
    if 'CLOUD_DEPLOYMENT_TIER=test' not in backend['Config']['Env']:
        raise SystemExit('Rehearsal runs only on a test site')
    sites = mount(containers['erp_backend'], '/home/frappe/frappe-bench/sites')
    site = sites / config['site']
    site_config = json.loads((site / 'site_config.json').read_text())
    if site_config.get('cloud_test_copy') is not True:
        raise SystemExit('Not a test copy')
    database = site_config['db_name']
    state = Path(config['state_root'])
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix='rehearse-cripple-', dir=state) as folder:
        data = Path(folder)
        mysql = ('export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mariadb-dump -uroot --single-transaction --routines '
                 '--triggers --hex-blob "$1"')
        sql_dump(['docker', 'exec', containers['erp_database'], 'sh', '-c', mysql, 'sh', database], data / 'erp.sql')
        postgres = ('export PGPASSWORD="$POSTGRES_PASSWORD"; exec pg_dump -U "$POSTGRES_USER" --no-owner --no-acl '
                    '"$POSTGRES_DB"')
        sql_dump(['docker', 'exec', containers['dms_database'], 'sh', '-c', postgres], data / 'dms.sql')
        for kind in ['public', 'private']:
            if (site / kind / 'files').exists():
                safe_copy(site / kind / 'files', data / 'erp-files' / kind)
        safe_copy(mount(containers['dms'], '/usr/src/paperless/media'), data / 'dms-media')
        safe_copy(mount(containers['dms'], '/usr/src/paperless/data'), data / 'dms-data')
        safe_copy(mount(containers['drive'], '/var/lib/ocis'), data / 'drive-data', exclude=['web/assets'],
                  allow_internal_links=True)
        (data / 'dms-consume').mkdir()
        (data / 'mail-data').mkdir()
        (data / 'document-enrollment.json').write_text(json.dumps({'users': []}) + '\n')
        before = {'erp': tokens_by_table(data / 'erp.sql'), 'dms': tokens_by_table(data / 'dms.sql')}
        kinds = {}
        names_before = drive_names(data / 'drive-data', kinds)
        blob_layout = None
        sample = next((m for m in (data / 'drive-data/storage/users/spaces').rglob('*.mpk')
                       if not m.is_symlink() and '.REV.' not in m.name
                       and unpack(m.read_bytes()).get('user.ocis.type') == b'1'), None)
        if sample is not None:
            from cripple_snapshot import split_id
            blobid = unpack(sample.read_bytes())['user.ocis.blobid'].decode()
            space = next(p for p in sample.parents if p.name == 'nodes').parent
            blob_layout = (space / 'blobs' / split_id(blobid)).is_file()
        counts_before = business_counts(containers, database)
        settings = {'cripple': {'enabled': True, 'days': days, 'keep_accounts': keep_accounts}}
        columns_found, names_found = {}, {}
        from cripple_snapshot import mysql_rows, sql_literal
        keep_sql = ','.join(sql_literal(a.casefold()) for a in keep_accounts + ['administrator', 'guest'])
        names = sorted({n.strip() for row in mysql_rows(containers['erp_database'], database,
                        'SELECT IFNULL(full_name,\'\') FROM `tabUser` '
                        f'WHERE LOWER(name) NOT IN ({keep_sql})') for n in row if len(n.strip()) >= 6 and ' ' in n.strip()})

        domains = audit_domains(config)

        def audits(container, name):
            column_audit(container, name, columns_found, domains)
            names_audit(container, name, names, names_found, keep_sql)
        result = cripple(data, settings, containers, database, business_counts, audit=audits)
        keep = {account.casefold().encode() for account in keep_accounts}
        report = {'names_checked': len(names), 'mail_domains_checked': len(domains), 'columns_still_holding_real_names': names_found,
                  'columns_still_holding_real_email_domains': columns_found, 'business_counts_before': counts_before, 'business_counts_after': result.pop('counts'),
                  'cripple': result, 'drive_blob_layout_confirmed': blob_layout}
        for name, path in [('erp', data / 'erp.sql'), ('dms', data / 'dms.sql')]:
            after = tokens_by_table(path)
            surviving = Counter()
            samples = {}
            for token, tables in after.items():
                if token in before[name] and token not in keep:
                    for table in tables:
                        surviving[table] += 1
                        samples.setdefault(table, []).append(masked(token))
            report[f'{name}_surviving_samples_masked'] = {t: sorted(set(v))[:4] for t, v in samples.items()}
            report[f'{name}_identifiers_before'] = len(before[name])
            report[f'{name}_identifiers_surviving_by_table'] = dict(surviving.most_common(40))
        names_after = drive_names(data / 'drive-data')
        report['drive_names_before'] = len(names_before)
        report['drive_original_names_surviving'] = len(names_before & names_after)
        survivors = Counter()
        for name in names_before & names_after:
            for kind in kinds.get(name, {'?'}):
                survivors['type ' + kind + (' (space/system name)' if name.isascii() and len(name) < 25 and b' ' not in name else '')] += 1
        report['drive_surviving_by_type'] = dict(survivors)
        report['drive_surviving_masked'] = sorted({masked(n) for n in names_before & names_after})[:25]
        files = [p for p in (data / 'erp-files').rglob('*') if p.is_file()]
        report['erp_files_not_placeholders'] = sum(1 for p in files if not re.fullmatch(r'file-[0-9a-f]{16}(\.[a-z0-9]+)?', p.name))
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, help='root-owned test refresh worker profile')
    parser.add_argument('--keep', action='append', default=[], help='account kept real (repeatable)')
    parser.add_argument('--days', type=int, default=60)
    args = parser.parse_args()
    os.umask(0o077)
    profile = Path(args.config)
    if profile.stat().st_uid != 0 or profile.stat().st_mode & 0o077:
        raise SystemExit('Configuration must be root-owned and private')
    config = json.loads(profile.read_text())
    if config.get('tier') != 'test':
        raise SystemExit('Test-only')
    print(json.dumps(rehearse(config, args.keep, args.days), indent=2, default=str))
