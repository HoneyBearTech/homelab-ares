# Interfaces

Everything homelab-ares reads, exposes or runs. homelab-ares has no HTTP API of its own; the services' web UIs
and APIs are documented by their projects.

## Settings

### `.env`

Read by `docker compose` from `.env` next to `compose.yaml` (template: [`.env.example`](../.env.example)). Every
setting is required: `docker compose` stops with an error naming any that's missing.

| Setting | Example | Meaning |
| --- | --- | --- |
| `TZ` | `Etc/UTC` | Time zone (tz database name) for logs and schedules. |
| `NPM_DATA_PATH` | `/srv/appdata/npm/data` | Host directory with Nginx Proxy Manager's settings database, proxy hosts and logs, mounted at `/data`. |
| `NPM_LETSENCRYPT_PATH` | `/srv/appdata/npm/letsencrypt` | Host directory with Nginx Proxy Manager's certificates, their private keys, the ACME account and any DNS-challenge credentials, mounted at `/etc/letsencrypt`. |
| `PROXY_NETWORK` | `homelab-ares_proxy` | Docker network Nginx Proxy Manager joins. Created once outside the stack (`docker network create`), so its address range survives rebuilding the stack. |
| `UPTIME_KUMA_VOLUME` | `homelab-ares_uptime-kuma` | Docker volume with Uptime Kuma's database, mounted at `/app/data`. |
| `PEANUT_CONFIG_PATH` | `/srv/appdata/peanut` | Host directory with PeaNUT's settings (including the NUT server's address and login) and its own login (`auth.yaml`, a bcrypt hash), mounted at `/config`. Must be writable by uid 1000, which PeaNUT runs as. |
| `PORTAINER_VOLUME` | `homelab-ares_portainer` | Docker volume with Portainer's database, mounted at `/data`. |

No secret is a setting. To adopt an existing installation, point each setting at the directory, volume or
network it already uses ([installing.md](installing.md#adopting-existing-containers)).

### `autoheal.env`

Read by the `autoheal` service (template: [`autoheal.env.example`](../autoheal.env.example)); optional, mode
`600`, gitignored.

| Setting | Meaning |
| --- | --- |
| `WEBHOOK_URL` | Where autoheal posts a notice each time it restarts a container (a secret). A Discord channel webhook works as is; empty or missing = log only |

### `backup.env`

Read by `scripts/scheduled-backup.sh` (template: [`backup.env.example`](../backup.env.example)); optional, mode
`600`, gitignored. Read as data, never run: only these keys, one `KEY=value` per line; anything else is an error.

| Setting | Default | Meaning |
| --- | --- | --- |
| `BACKUP_DIR` | `backups` | Where backups are written (relative to the checkout, or absolute). |
| `BACKUP_KEEP` | `3` | How many backups are kept in `BACKUP_DIR`; older ones are deleted. |
| `BACKUP_REMOTE` | empty | rsync destination each backup is copied to, such as `backup-host:/volume1/ares-backups` (an SSH alias); empty = no copy. |
| `BACKUP_REMOTE_KEEP` | `30` | How many backups are kept at `BACKUP_REMOTE`; older ones are deleted. |
| `BACKUP_PING_URL` | empty | An Uptime Kuma push URL (a secret), told `up` after each good run and `down` after a failed one. |

Only directories named like a backup (`<date>-<time>`) are ever deleted, here or at the remote.

## Services and ports

| Service | Image | Host port → container | What |
| --- | --- | --- | --- |
| `npm` | `jc21/nginx-proxy-manager` | 80 → 80, 443 → 443 | Proxied HTTP and HTTPS |
| | | 81 → 81 | Admin UI (LAN only) |
| `uptime-kuma` | `louislam/uptime-kuma` (slim) | 3001 → 3001 | Web UI and status pages; no "Real Browser" monitors (the slim image has no Chromium) |
| `peanut` | `brandawg93/peanut` | 8080 → 8080 | Web UI, API and Prometheus metrics (`/api/v1/metrics`), behind PeaNUT's login (HTTP Basic auth works for scrapers); `/api/ping` is open |
| `portainer` | `portainer/portainer-ce` (Alpine variant) | 9443 → 9443 | Web UI (HTTPS) |
| | | 8000 → 8000 | Tunnel for Edge agents |
| `autoheal` | `willfarrell/autoheal` | none | Restarts any labelled service whose health check fails |
| `socket-proxy` | `lscr.io/linuxserver/socket-proxy` | none (internal network `docker-proxy`) | Filtered Docker API for autoheal |

Ports are published on every host interface. Every service has a health check (`docker compose ps` shows it).
Exact versions and digests are in [`compose.yaml`](../compose.yaml).

## Volumes and mounts

| Container path | Host source | Service |
| --- | --- | --- |
| `/data` | `NPM_DATA_PATH` | npm: settings database, proxy host configuration, logs |
| `/etc/letsencrypt` | `NPM_LETSENCRYPT_PATH` | npm: TLS certificates and their private keys |
| `/app/data` | volume `UPTIME_KUMA_VOLUME` | uptime-kuma: database |
| `/config` | `PEANUT_CONFIG_PATH` | peanut: settings |
| `/data` | volume `PORTAINER_VOLUME` | portainer: database, users, environments |
| `/var/run/docker.sock` | the Docker socket | portainer (read-write), socket-proxy (read-only); allowed exceptions, see below |

## Networks

| Network | Who | Meaning |
| --- | --- | --- |
| `PROXY_NETWORK` | npm | External: created once, outside the stack; keeps its address range when the stack is recreated |
| `default` | uptime-kuma, peanut, portainer, autoheal | The stack's own network |
| `docker-proxy` | socket-proxy, autoheal | Internal: no route out, nothing published |

## Labels

| Label | Meaning |
| --- | --- |
| `org.honeybeartech.ares.allow.<rule>` | Lets one service break one policy rule; the value is the reason, and must not be empty. Rules: `image`, `digest`, `latest`, `build`, `privileged`, `no-new-privileges`, `cap-drop`, `cap-add`, `host-network`, `host-pid`, `docker-socket`, `healthcheck` ([security.md](security.md#policy)). In use: `portainer` and `socket-proxy` (`docker-socket`), `autoheal` (`latest`). |
| `autoheal` | `"true"` on every service autoheal may restart when its health check fails: npm, uptime-kuma, peanut, portainer and socket-proxy. |

## Commands

| Command | Does |
| --- | --- |
| `docker compose up -d` / `down` / `ps` / `logs <service>` | Runs and inspects the stack |
| `make check` | `docker compose config --format json \| python scripts/check_compose.py`: the policy check |
| `python scripts/check_compose.py [FILE] [--sbom OUT]` | Checks a resolved Compose config (from `FILE` or stdin); `--sbom` also writes a CycloneDX 1.6 SBOM of the images. Exit 0 = no violations, 1 = violations (one line each), 2 = unreadable input |
| `make test`, `make lint` | The checker's tests and the linters |
| `scripts/backup.sh [DIR]` | Archives every service's data mounts (every read-write volume or bind mount except the Docker socket and anonymous volumes), `.env` and any `<service>.env` into `DIR` (default `backups/<date>-<time>`, gitignored) with a `MANIFEST`, `NETWORKS` (the address range of each network the stack uses but doesn't create), `VERSION` (the checkout's `git describe`) and `SHA256SUMS`, all mode `600`. Each service is stopped only while its own mounts are archived and started again if it was running. Exit 0 = backup complete |
| `scripts/scheduled-backup.sh` | Runs `scripts/backup.sh` into `BACKUP_DIR/<date>-<time>`, copies it to `BACKUP_REMOTE` with rsync (`SHA256SUMS` last), deletes all but the newest `BACKUP_REMOTE_KEEP` there and `BACKUP_KEEP` here, and reports to `BACKUP_PING_URL` ([`backup.env`](#backupenv)). Run nightly by the systemd user units in `deploy/systemd/`. Exit 0 = backup complete and copied |
| `scripts/restore.sh [--yes] DIR [SERVICE...]` | Verifies `DIR/SHA256SUMS`, checks the `MANIFEST`, creates missing containers and volumes, asks for confirmation (unless `--yes`), stops the services, replaces the contents of each listed mount with its archive (owners and modes kept), and starts what was running. Writes only mounts the service still has read-write; never the Docker socket |
| `make smoke` | `scripts/smoke-test.sh`: starts every service under a separate Compose project with throwaway directories, volumes and networks, no fixed container names, no published ports and no env files; waits until all are healthy, checks that Uptime Kuma can ping, round-trips a backup and restore over every data mount, runs the scheduled backup against a stand-in backup server, makes a test container unhealthy and checks that autoheal restarts it, then removes what it created. Exit 0 = all passed |

## Outbound connections

From the host: the image registries (Docker Hub, `lscr.io`) on `docker compose pull`. From the services: Nginx
Proxy Manager to the backends it proxies and to Let's Encrypt; Uptime Kuma to what it monitors and to its
notification channels; PeaNUT to the NUT server; Portainer to the agents on the other Docker hosts; autoheal to
its webhook, if one is set. The scheduled backup to `BACKUP_REMOTE` (rsync, usually over SSH) and to
`BACKUP_PING_URL`, if they are set.

## Release files

Each GitHub Release has `homelab-ares-<version>.tar.gz` (source, with `LICENSE`),
`homelab-ares-<version>.cdx.json` (CycloneDX SBOM of the pinned images), `SHA256SUMS` and its Sigstore bundle,
and SLSA provenance ([verifying-releases.md](verifying-releases.md)).
