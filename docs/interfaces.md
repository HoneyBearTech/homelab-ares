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
| `CONFIG_ROOT` | `/srv/config` | Host directory holding every service's data, one folder per service (`CONFIG_ROOT/<service>/config` and beside it any other folder of the service's own; see [Volumes and mounts](#volumes-and-mounts)). Never a path inside `/var/lib/docker/volumes` ([installing.md](installing.md#where-data-lives)). |
| `PROXY_NETWORK` | `homelab-ares_proxy` | Docker network Nginx Proxy Manager joins. Created once outside the stack (`docker network create`), so its address range survives rebuilding the stack. |

No secret is a setting. To adopt an existing installation, copy each service's data into its folder under
`CONFIG_ROOT` and point `PROXY_NETWORK` at the network the old proxy uses
([installing.md](installing.md#adopting-existing-containers)).

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

### Environment

Read by `scripts/backup.sh` and `scripts/restore.sh` for the [deploy lock](installing.md#deploy-lock) they share
with the pull agent; nothing needs setting on a normal host.

| Variable | Default | Meaning |
| --- | --- | --- |
| `HOMELAB_PULL_STATE_DIR` | `$XDG_STATE_HOME/homelab-pull` | The pull agent's state root, as the agent reads it. If it has no `ares` directory, no lock is taken. |
| `XDG_STATE_HOME` | `~/.local/state` | Used for the state root when `HOMELAB_PULL_STATE_DIR` isn't set. |

## Services and ports

| Service | Image | Host port → container | What |
| --- | --- | --- | --- |
| `npm` | `jc21/nginx-proxy-manager` | 80 → 80, 443 → 443 | Proxied HTTP and HTTPS |
| | | 81 → 81 | Admin UI (LAN only) |
| `uptime-kuma` | `louislam/uptime-kuma` (slim) | 3001 → 3001 | Web UI and status pages; no "Real Browser" monitors (the slim image has no Chromium) |
| `peanut` | `brandawg93/peanut` | 8080 → 8080 | Web UI, API and Prometheus metrics (`/api/v1/metrics`), behind PeaNUT's login (HTTP Basic auth works for scrapers); `/api/ping` is open |
| `portainer` | `portainer/portainer-ce` (Alpine variant) | 9443 → 9443 | Web UI (HTTPS). Agents connect the standard way; 8000, the tunnel for Edge agents, isn't published |
| `autoheal` | `willfarrell/autoheal` | none | Restarts any labelled service whose health check fails |
| `socket-proxy` | `lscr.io/linuxserver/socket-proxy` | none (internal network `docker-proxy`) | Filtered Docker API for autoheal |

Ports are published on every host interface. Every service has a health check (`docker compose ps` shows it).
Exact versions and digests are in [`compose.yaml`](../compose.yaml).

## Volumes and mounts

Every service's data is in a host directory under `CONFIG_ROOT`; the stack declares no Docker volumes.

| Container path | Host source | Service |
| --- | --- | --- |
| `/data` | `CONFIG_ROOT/npm/config` | npm: settings database, proxy host configuration, logs (`/data/logs`, not backed up) |
| `/etc/letsencrypt` | `CONFIG_ROOT/npm/letsencrypt` | npm: TLS certificates, their private keys, the ACME account and any DNS-challenge credentials |
| `/var/lib/logrotate` | `CONFIG_ROOT/npm/logrotate` | npm: when each log in `/data/logs` was last rotated |
| `/app/data` | `CONFIG_ROOT/uptime-kuma/config` | uptime-kuma: database |
| `/config` | `CONFIG_ROOT/peanut/config` | peanut: settings (including the NUT server's address and login) and its own login (`auth.yaml`, a bcrypt hash); must be writable by uid 1000, which PeaNUT runs as |
| `/data` | `CONFIG_ROOT/portainer/config` | portainer: database, users, environments |
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
| `org.honeybeartech.ares.allow.<rule>` | Lets one service break one policy rule; the value is the reason, and must not be empty. Rules: `image`, `digest`, `latest`, `build`, `privileged`, `no-new-privileges`, `cap-drop`, `cap-add`, `host-network`, `host-pid`, `docker-socket`, `devices`, `healthcheck` ([security.md](security.md#policy)). In use: `portainer` and `socket-proxy` (`docker-socket`), `autoheal` (`latest`). |
| `autoheal` | `"true"` on every service autoheal may restart when its health check fails: npm, uptime-kuma, peanut, portainer and socket-proxy. |
| `org.honeybeartech.ares.backup.skip` | Container paths (comma-separated, exact) that `scripts/backup.sh` never archives and `scripts/restore.sh` refuses to write, even if a backup lists them: data too large to back up here or disposable. Not in use. |
| `org.honeybeartech.ares.backup.exclude` | Paths inside a service's data mounts (comma-separated, exact container paths, at any depth) that `scripts/backup.sh` leaves out of the mount's archive and `scripts/restore.sh` leaves in place. A path that isn't inside one of the service's data mounts, or contains `..` or a pattern character (`*?[\`), makes both fail before anything stops. In use: npm (`/data/logs`). |

## Commands

| Command | Does |
| --- | --- |
| `docker compose up -d` / `down` / `ps` / `logs <service>` | Runs and inspects the stack |
| `make check` | `docker compose config --format json \| python scripts/check_compose.py`: the policy check |
| `python scripts/check_compose.py [FILE] [--sbom OUT]` | Checks a resolved Compose config (from `FILE` or stdin); `--sbom` also writes a CycloneDX 1.6 SBOM of the images. Exit 0 = no violations, 1 = violations (one line each), 2 = unreadable input |
| `make test`, `make lint` | The checker's tests and the linters |
| `scripts/backup.sh [DIR]` | Archives every service's data mounts (every read-write volume or bind mount except the Docker socket, anonymous volumes and the paths in the service's `backup.skip` label; a mount inside another mount is archived on its own and left out of the outer archive), `.env` and any `<service>.env` into `DIR` (default `backups/<date>-<time>`, gitignored) with a `MANIFEST`, `NETWORKS` (the address range of each network the stack uses but doesn't create), `VERSION` (the checkout's `git describe`) and `SHA256SUMS`, all mode `600`. Each service is stopped only while its own mounts are copied and started again (with any service Compose stopped along with it) before the copies are compressed (with `pigz` when it's installed, else `gzip`). Leaves out the paths a service's `org.honeybeartech.ares.backup.exclude` label lists. Waits for a deploy by the pull agent and holds its lock until it exits ([deploy lock](installing.md#deploy-lock)). If stopping a service fails while its container is still on its way down (a process stuck writing to a network share can outlast Docker's stop), it waits up to `BACKUP_STOP_WAIT` seconds (default 120) for the container to exit and carries on; if it still runs then, the backup fails, and the services are started again only after a second wait. Fails, naming them, if any service that was running when it began isn't running again at the end. Exit 0 = backup complete |
| `scripts/scheduled-backup.sh` | Runs `scripts/backup.sh` into `BACKUP_DIR/<date>-<time>`, copies it to `BACKUP_REMOTE` with rsync (`SHA256SUMS` last), deletes all but the newest `BACKUP_REMOTE_KEEP` there and `BACKUP_KEEP` here, and reports to `BACKUP_PING_URL` ([`backup.env`](#backupenv)). Run nightly by the systemd user units in `deploy/systemd/`. Exit 0 = backup complete and copied |
| `scripts/restore.sh [--yes] DIR [SERVICE...]` | Verifies `DIR/SHA256SUMS`, checks the `MANIFEST`, creates missing containers, asks for confirmation (unless `--yes`), stops the services, recreates a container made from an older `compose.yaml` (a missing directory is created), replaces the contents of what the service mounts at each listed container path now with its archive (owners and modes kept; a backup of a Docker volume restores into the directory that replaced it), and starts what was running. Writes only mounts the service still has read-write; never the Docker socket, a path in the service's `backup.skip` label, another mount inside the one it restores, or a path in its `backup.exclude` label. Takes the pull agent's lock first, as `backup.sh` does |
| `make smoke` | `scripts/smoke-test.sh`: starts every service under a separate Compose project with throwaway directories (`CONFIG_ROOT` among them), volumes and networks, no fixed container names, no published ports and no env files; waits until all are healthy, checks that Uptime Kuma can ping, round-trips a backup and restore over every data mount (one service's through a recreated container into a config directory that was removed), runs the scheduled backup against a stand-in backup server, makes a test container unhealthy and checks that autoheal restarts it, then removes what it created. Exit 0 = all passed |

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
