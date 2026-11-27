# Drive: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 28 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Drive: P items

oCIS Drive: web, desktop and phone clients, spaces, calendar and contact sync.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P10 — Desktop/iPhone Drive and calendar/contact clients

**App:** drive · **Also touches:** mail · **State:** open

**Status:** native ownCloud desktop synchronization is available and Drive web/Desktop/iOS SSO clients are configured and display Drive; actual device/folder-sync completion is not established after the hostname changes. A new custom desktop-sync implementation is not pending.

- Verify ownCloud iPhone sign-in, callback and file access using https://drive.example.com/.
- Choose the Desktop local sync folder and verify actual upload/download synchronization; preserve existing local files.
- Check required desktop platforms, shared folders/Spaces, offline conflicts, rename/delete propagation, interrupted transfers and token revocation. Server revocation does not erase local downloaded copies. See [desktop reconciliation](../roadmap.md#4-native-drive-desktop-synchronization).
- Verify native CalDAV/CardDAV discovery, authentication and synchronization on the intended devices. Earlier server protocol round trips passed, but device acceptance remains due.
