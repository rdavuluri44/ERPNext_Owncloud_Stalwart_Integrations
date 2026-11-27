# Workspace monitoring

## Purpose

Run the probes on a host independent of the services it watches. They use
Python's standard library and require outbound HTTPS. Redirects are reported
at the target route, and each configured route has its own expected status.
The probes verify TLS, make no authenticated requests and discard response
bodies. A successful status shows that the monitored route answered.

## Contents

- `https_probe.py` for HTTPS and optional TCP targets
- `job_probe.py` and systemd units for backup and restore-drill reports
- `cloud-https-monitor.service` and `cloud-https-monitor.timer`

## Requirements

Python 3 with its standard library, trusted CA certificates, outbound HTTPS
and systemd for scheduled runs.

## Reuse

Install `https_probe.py` in `/opt/cloud-monitoring`, the unit files in the
systemd unit directory and a host-specific `targets.json` in
`/etc/cloud-monitoring`. The config must be readable by the dynamic service
user. Keep credentials out of the URLs and the target labels.

## Configuration

```json
[
  {"name": "Website", "url": "https://example.com/", "statuses": [200], "minimum_certificate_days": 14},
  {"name": "Document manager", "url": "https://dms.example.com/", "statuses": [302]},
  {"name": "Storage host", "kind": "tcp", "host": "storage.example.com", "port": 443}
]
```

Install and enable `cloud-backup-monitor.timer` only where the production
backup reports are written. Enable `cloud-restore-drill-monitor.timer` on
the test host. Their units read the existing private reports every five
minutes, with freshness limits of 26 hours and eight days respectively. If
the report directories differ, configure the service command accordingly.
The checks do not start backup or restore jobs. TCP checks establish that a
private port accepts connections. Use native host alerts to monitor storage.

## Tests

Run `python3 tests/test_https_monitor.py` from the repository root.

Check locally with `python3 https_probe.py targets.json`. Exit status 1
means at least one probe failed, and status 2 means the configuration is
invalid. Enable the timer with `systemctl enable --now cloud-https-monitor.timer`.
Read the checks through `journalctl -u cloud-https-monitor.service`.
This module provides probe results for an operator or notification integration.

## Licenses

The module uses the repository license and ships no external dependencies.

AI-assisted development by Codex.

## Metrics and logs

The Compose files in `observability/` use immutable upstream images for
Prometheus, Grafana, Loki, Alloy, node_exporter and cAdvisor. Start the
dashboard and storage components with the `central` profile. The default
bindings are loopback. Use a private HTTPS proxy for the dashboard. Keep
the required `admin_password` file, deployment URL and private scrape target
addresses outside Git. Set the password file to root:root and mode 0440 for the pinned Grafana
image, which runs with GID 0. Verify the configured administrator can
sign in before enabling the private proxy. Never include credentials in metric labels or logs.

Every service uses `restart: always` (P57, 26 November 2026): after a production reboot Prometheus once stayed
down for 26 minutes although it had `unless-stopped`, and with it every metric alert. `always` starts a container
whenever Docker starts, whatever happened before, so on a host that runs only the exporters, **remove** the four
central containers instead of leaving them stopped: `docker compose rm -s -f prometheus loki alloy grafana`
(their named volumes stay). The host's boot check also starts, once, any container that ran before a reboot and
did not come back (`tools/host_check.py`).

The exporters can run alone on a watched host. Where a remote Prometheus
requires access, set `METRICS_BIND` to its private network address. cAdvisor
uses read-only host mounts and local Docker and containerd sockets to read
container metrics. cAdvisor collects CPU, memory, network and OOM metrics.
Host disk capacity is collected by node_exporter. Keep the exporters isolated from application networks.
Allow access to the exporter ports only over the private monitoring network.

Prometheus keeps 14 days of metrics up to its configured size limit.
Loki keeps the allowlisted monitoring journal streams for seven days. Alloy
collects the HTTPS, backup and restore monitor units. The initial deployment
does not ingest arbitrary application logs. The dashboard and Prometheus
rules cover host capacity, exporter reachability and container usage.
The rules are visible through Prometheus. No external alert channel is
configured by this module.

For a local test, run `docker compose --profile central config --quiet`,
check the Prometheus config and rules with `promtool`, and verify a fresh
Prometheus sample and a Loki query against the running collectors.
