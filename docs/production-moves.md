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

The server restarts every container by itself (`restart: unless-stopped`),
Tailscale is brought up before Docker, and the **boot check** runs once Docker
is up (`tools/host_check.py boot`; its result is in
`/var/lib/cloud-host-check/status.json` and the journal:
`journalctl -u cloud-boot-check`). A restart-count **watch** runs every five
minutes (`restart-alerts.json`, journal lines starting `ALERT`). Verify by hand
only when the check reports a problem:

1. `systemctl status cloud-boot-check` is `active (exited)`; otherwise read its
   journal: it names what stays wrong (a missing container, a host answering
   with an error, a port not listening, the editor bridge not registered).
2. All containers running, none restarting: `docker ps --filter
   status=restarting` is empty.
3. ERP, sign-in, Drive, Mail, DMS and the editor host answer (the check does
   this over HTTP; open the portal once in a browser).
4. **Drive opens a document** in the editor (a download offer means the bridge
   is not registered).
5. Tailnet-bound services listen (private DNS, mail on the tailnet and relay
   addresses): the check tests the ports you list in the private profile.
6. The next nightly backup finds its containers (names in the backup profile).
7. Note the cause of the restart in the release record.

## Planned reboot procedure

Reboot for kernel updates deliberately, at night, not by accident:

1. Announce it; pick a time away from the nightly backup (02:34 server time)
   and from any refresh or deploy.
2. Take a rollback note (running containers, image tags) and make sure the
   last backup succeeded.
3. Check that the boot check and watch units are installed and enabled, and
   that Docker waits for Tailscale (`systemctl cat docker` shows the drop-in).
4. `systemctl reboot`; expect one to two minutes of downtime for every app.
5. Follow the checklist above; record the downtime and any repair the boot
   check made.
6. Rehearse on the test host first after changes to these files: reboot it,
   run the checklist, then restart oCIS five times in a row and check the
   bridge each time.

## Installing the host checks

On the host, from a checkout of this repository (the profile is private and
stays outside Git; its optional `host_checks` section lists container prefixes,
tailnet-bound ports and the tailnet address, see
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
