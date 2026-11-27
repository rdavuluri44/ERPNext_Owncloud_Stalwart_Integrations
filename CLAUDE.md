# Instructions for Claude

The development and release policy in AGENTS.md is mandatory and
nonnegotiable. Read it before making any change, and follow it for every
change, including urgent fixes:

repository commit and push → deploy to the permanent test site → validate
there → promote that same tested revision to production.

Never develop directly in production or deploy uncommitted changes.

## Session routine (owner, 21 November 2026)

Two repositories: this **public** one (code, module READMEs, `docs/decisions.md`)
and a **private operations repository**. Use the project folder map to locate
its checkout and read its current `main` branch. The private
repository holds only records and private assets: the pending and priority list
(`docs/pending.md`), the production release log (`docs/production-releases.md`),
runbooks, handovers (`docs/handover-<date>.md`), deliberations, and clients' brand
assets such as their logos (our own Unformat brand is public, in `branding/`). It never holds secrets (see AGENTS.md); those stay on the servers
and in the owner's password manager.

Do these without being asked:

1. **At the start of a session:** read AGENTS.md, then the newest handover in the
   private repository, the "How to use this list" and "Priority order" sections at
   the top of its `docs/pending.md`, and the open pull requests here (`gh pr list`).
   Summarise the state briefly. The owner decides what starts; do not push for it.
2. **After every merge and production update** (and after every incident or live
   change): update the private repository in the same session (release entry with the
   tested commit, rollback point and what test could not cover; the P item status)
   and push it.
3. **When the owner closes the session:** write or extend today's handover in the
   private repository (done, open items most urgent first, decisions, any secret that
   was exposed) and push it. Keep it current at milestones in case a session ends
   abruptly.
4. **P items:** related items are taken up together, tested together and merged as one
   release; each keeps its own status (see `docs/decisions.md`).
5. **Publish the P list:** the P list is organised by app: the private `docs/pending.md` is the
   index and each item lives in `docs/pending/<app>.md` (`general` for platform and security
   items). Whenever any of them changes (new item, scope, state or priority), run
   `tools/p_index.py` and then regenerate the public `docs/p-list.md` and `docs/p-list/` in the same
   session with the private repository's `tools/publish_p_list.py`, and open a pull request here (the
   owner merges). **Never skip details:** the tool changes text inside lines only, never removes or
   summarises a line, and lists every substitution in its report; redact only the categories
   in its private rules file (organisation name, host names, IP addresses, server paths and
   rollback folders, mail addresses, names of people and third parties' internal products,
   business file names, links to private records). The leak scan must be clean and the
   report must be read before the pull request is opened.
6. **Only open work is listed:** remove a P item from its app list when the task is completed, or
   becomes redundant or irrelevant, in the same session (`tools/p_close.py` in the private
   repository); it leaves one line in the closed log (`docs/p-closed.md`) so numbers are never
   reused. Then refresh the index and publish as in step 5.

@AGENTS.md
