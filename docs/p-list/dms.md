# DMS: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 27 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# DMS: P items

Paperless document management and the Drive-to-Paperless processing worker.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P20 — Paperless document links on ERP transactions

**App:** dms · **Also touches:** erp · **State:** open

**Status:** revised integration work pending; replaces the former direct object-storage/S3 task. Paperless and the Drive processing worker are already deployed, but the read-only ERP schema audit found no DMS/Paperless transaction-link fields.

Keep authoritative scans/OCR in Paperless and associate stable document IDs/links with ERP transactions through permission-checked upload/select/link flows. Agree eligible document classes, fields, shared references, retry/processing status and access/revocation behavior. Preserve historical associations and originals until any migration is copied, verified and accepted. Existing Drive originals are not deleted by this plan. Test previews, exports/printing/email dependencies and consistent ERP+DMS recovery. See [revised transaction design](../roadmap.md#6-erp-transactions-reference-paperless-documents).
