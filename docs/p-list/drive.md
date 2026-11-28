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

### P115 — Drive inside the Desk: header band removed, Spaces first, one look for folders

**App:** drive · **Also touches:** portal · **State:** open

**Status:** recorded 28 November 2026 (owner, with three screenshots of the test site); **nothing built**. Not
ranked yet.

**What the owner asked for**
1. The blue header band goes; the Desk's top bar (P111) takes that place. Its search and bell are replaced by the
   universal ones, its account button by the Desk's user button.
2. **Preferences** moves from the account button to the left pane, beneath Deleted files.
3. The **"open side bar"** button moves down, to the left of the view buttons.
4. Drive **opens straight into Spaces**, not Personal.
5. A space's **top level looks like a folder inside a space**: the path line with the three dots beside the current
   name, without the large tile.

**To settle in the design:** the large tile carries the space's picture and description; without it they are not
shown (the three-dots menu with members, rename and the rest stays beside the name). The version line at the
bottom left stays; the same versions appear in About.

**Records:** register entries for each overlay or setting on Drive's screens, in the same pull request (see P111).
