# Moving a running service onto the repository build

How an app that was first set up by hand (a "legacy" Coolify service) is moved
onto the stack rendered from this repository, without losing data and with a
pause of seconds. Used for the ERP, the office editor, Drive, DMS, Mail and
private DNS in November 2026. The dated records, with real addresses and
service IDs, are kept in the maintainers' private operations repository.

## Why

Production must be reproducible from Git. A hand-made service drifts, and a
Coolify redeploy can silently restore old settings. After a move, every
setting comes from a tested release plus a private profile outside Git.

## Steps

1. **Release and gate.** The change is committed, pushed and validated on the
   test site first (see `AGENTS.md`).
2. **Private production profile.** Outside Git, next to the other secrets.
   The renderer (`tools/prepare_runtime.py`) supports the options a move
   needs:
   - `existing_volumes`: reuse the legacy service's named data volumes;
   - `existing_mounts`: reuse persistent bind-mounted directories;
   - `extra_networks`: keep old network aliases that other services still use;
   - `production_bindings`: production-only host ports and `extra_hosts`
     (validated: IPv4 host addresses only);
   - `production_mail_ports`: the mail ports, for the Mail stack only.
3. **Carry the settings.** Take every setting from the legacy service. Inside
   one compose file, a key in `environment` **overrides** the same key in an
   `env_file`, so merge as `{**env_file, **environment}`. Then compare the
   environment of the new containers with the **running** legacy containers
   (`docker inspect -f '{{json .Config.Env}}'`), not with reconstructed files.
   (A Mail move once lost the portal from webmail's allowed frame ancestors
   because the merge order was reversed and the comparison repeated it.)
4. **Route file.** Replace the legacy container labels with a Traefik file
   route rendered from `deployment/production/*.traefik.yaml` (written for
   `example.com`; the deployment substitutes the real domain). Check routes
   that point at the old router names elsewhere (for example an ACME challenge
   route for the mail server's own certificate).
5. **Rollback point.** Copy the legacy compose file, its `.env`, env files and
   affected route files to a dated folder with checksums.
6. **Register and switch.** Register the rendered stack with Coolify
   (`tools/coolify_native.py`), stop the legacy containers (restart policy
   off, nothing deleted), start the new stack and install the route file.
7. **Verify** what users rely on: pages, sign-in, framing inside the portal,
   protocols (SMTP, IMAP, DNS), and that the data is the existing data.
8. **Backups and test refresh.** Point the backup profile and the test-refresh
   exporter at the new container names, and check that every container they
   name exists.
9. **Owner check, then delete.** After the owner confirms, delete the legacy
   service with Coolify's own delete, keeping volumes the new stack uses.
10. **Record** the move (release record, decisions, module README).

## Office editor note

Drive's service (oCIS) registers one of its own internal addresses in a service
registry, chosen at random at every start, and the editor bridge
(collaboration) reaches oCIS at that address. The bridge is therefore put on
**every network oCIS is on** by the renderer (`NETWORK_PEERS` in
`tools/prepare_runtime.py`, tested), starts only after oCIS reports healthy,
and the post-boot check restarts it once if it cannot register. If documents
download instead of opening: look at the bridge's log for `AddAppProvider
failed` / `i/o timeout`; the cause is a missing shared network, not the
editor.

## After a reboot or restart: checklist

The server restarts every container by itself (`restart: unless-stopped`; the monitoring stack uses
`restart: always` since Prometheus once stayed down after a reboot, 26 November 2026), Tailscale is brought up
before Docker, and the **boot check** runs once Docker is up (`tools/host_check.py boot`; its result is in
`/var/lib/cloud-host-check/status.json` and the journal: `journalctl -u cloud-boot-check`). A restart-count
**watch** runs every five minutes (`restart-alerts.json`, journal lines starting `ALERT`) and saves the list of
running containers (`running-containers.json`). After a reboot the boot check compares with that list: a
container that ran before (restart policy `always` or `unless-stopped`) and is not running a minute after Docker
started is **started once**, and anything that still stays down fails the check. When the check repaired or
failed something it **mails the admin** through the dedicated alert sender (`host_checks.alert` in the private
profile; without it the result is only in the status file and the journal; set `host_checks.alert.address` to
the mail server's tailnet address when the server cannot reach its own public mail name, the certificate is still
verified for `smtp_host`). Verify by hand only when the check
reports a problem:

1. `systemctl status cloud-boot-check` is `active (exited)`; otherwise read its
   journal: it names what stays wrong (a missing container, a host answering
   with an error, a port not listening, the editor bridge not registered).
2. All containers running, none restarting: `docker ps --filter
   status=restarting` is empty. `status.json` lists what the check started after the reboot
   (`started_after_reboot`) and what it could not start (`could_not_start`); find out why each did not come back
   by itself and note it in the release record.
3. **The monitoring stack is back:** on the central host Prometheus, Grafana, Loki and Alloy, and the two exporters
   (node_exporter, cAdvisor) on every watched host; Prometheus answers on its port and has fresh samples. Without
   it no metric alert can fire.
4. ERP, sign-in, Drive, Mail, DMS and the editor host answer (the check does
   this over HTTP; open the portal once in a browser).
5. **Drive opens a document** in the editor (a download offer means the bridge
   is not registered).
6. Tailnet-bound services listen (private DNS, mail on the tailnet and relay
   addresses): the check tests the ports you list in the private profile.
7. The next nightly backup finds its containers (names in the backup profile).
8. Note the cause of the restart in the release record.

## Planned reboot procedure

Reboot for kernel updates deliberately, at night, not by accident:

1. Announce it; pick a time away from the nightly backup (02:34 server time)
   and from any refresh or deploy.
2. Take a rollback note (running containers, image tags) and make sure the
   last backup succeeded.
3. Check that the boot check and watch units are installed and enabled, and
   that Docker waits for Tailscale (`systemctl cat docker` shows the drop-in).
4. Stop the editor first so it saves every open document to Drive
   (`docker stop -t 300 <editor container>`; Docker gives containers only 15 s
   when the host shuts down), then `systemctl reboot`; expect one to two minutes
   of downtime for every app. The editor file safety watch rescues anything
   parked after the restart (P61, `integrations/onlyoffice/README.md`).
5. Follow the checklist above; record the downtime and any repair the boot
   check made.
6. Rehearse on the test host first after changes to these files: reboot it,
   run the checklist, then restart oCIS five times in a row and check the
   bridge each time.

## Installing the host checks

On the host, from a checkout of this repository (the profile is private and
stays outside Git; its optional `host_checks` section lists container prefixes,
tailnet-bound ports and the tailnet address, and `check_bridge: true` when the
profile used has no Drive project but the server runs Drive, see
`deployment/host-checks.example.json`):

    python3 tools/render_host_checks.py --profile /path/to/profile.private.json --output /tmp/host-checks
    install -d /opt/cloud-host-check /etc/cloud-host-check
    install -m 0755 tools/host_check.py /opt/cloud-host-check/host_check.py
    install -m 0644 /tmp/host-checks/config.json /etc/cloud-host-check/config.json
    install -m 0644 /tmp/host-checks/cloud-*.service /tmp/host-checks/cloud-*.timer /etc/systemd/system/
    install -d /etc/systemd/system/docker.service.d
    install -m 0644 /tmp/host-checks/docker.service.d/10-after-tailscale.conf /etc/systemd/system/docker.service.d/
    systemctl daemon-reload && systemctl enable cloud-boot-check.service cloud-restart-watch.timer
    systemctl start cloud-restart-watch.timer

`daemon-reload` does not restart Docker or any container; the Docker drop-in
takes effect at the next Docker start. Test the boot check without rebooting
with `python3 /opt/cloud-host-check/host_check.py boot --config /etc/cloud-host-check/config.json`.

## Releasing a merged change: no stack left behind (P59)

1. **Plan.** `python3 tools/promotion_plan.py <commit production runs> origin/main` lists
   every stack, setup step, live setting and restart the release reaches, and what the test
   site could not cover. The pull request carries the same list; the release record keeps it.
2. **Rollback point** for every stack in the list (image tags, compose and profile copies).
3. **Promote every stack in the list**, not only the ERP: build where the plan says, render
   and redeploy, run the setup steps, apply the live settings, restart what it names.
4. **Check what test could not cover** right after promotion (browser and protocol checks).
5. **Drift check.** `python3 /opt/cloud-drift-check/repository/tools/drift_check.py --config
   /etc/cloud-drift-check/config.json` must report every stack clean (exit 0). The release
   is not finished while it reports drift.

Install the nightly check on the production host: a read-only clone of this repository in
`/opt/cloud-drift-check/repository`, the settings from `deployment/drift-check.example.json`
in `/etc/cloud-drift-check/config.json` (root only), and `deployment/drift-check.service.example`
plus `deployment/drift-check.timer.example` in `/etc/systemd/system/` (without `.example`),
then `systemctl enable --now drift-check.timer`.

**The ERP core image and the nightly cleanup.** The ERP add-on image is built on the core
image (`cloud-integrations/erp-core:<version>`). No container runs the core image itself, so
Coolify's scheduled Docker cleanup, which removes unused images, deletes it, and the next ERP
release first rebuilds it (about 20 minutes). Until P71 (build once, keep every build in a
registry) removes the problem, plan that time into ERP releases. Before relying on any
workaround (for example excluding the image from the cleanup), check which cleanup commands
the installed Coolify version runs.
