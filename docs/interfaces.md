# Interfaces

Everything homelab-ares reads, exposes or runs. homelab-ares has no HTTP API of its own; the services' web UIs
and APIs are documented by their projects.

> **Planned:** `compose.yaml` isn't in the repository yet. The settings, services, ports and mounts below are
> the expected ones (the upstream defaults); they are confirmed or corrected when the stack is added. The
> scripts and commands already exist.

## Settings

### `.env`

Read by `docker compose` from `.env` next to `compose.yaml` (template: [`.env.example`](../.env.example)). A
setting marked required stops `docker compose` with an error naming it when it's missing.

| Setting | Required | Example | Meaning |
| --- | --- | --- | --- |
| `TZ` | yes | `Etc/UTC` | Time zone (tz database name) for logs and schedules. |
| `APPDATA_ROOT` | yes | `/srv/appdata` | Host directory for the services' data, one subdirectory each. Holds certificates and logins. |

No secret is a setting. If a service ever needs one in its environment, it gets its own gitignored
`<service>.env` (mode `600`) with a committed `<service>.env.example`, listed here.

## Services and ports

| Service | Image | Host port → container | What |
| --- | --- | --- | --- |
| Nginx Proxy Manager | `jc21/nginx-proxy-manager` | 80 → 80, 443 → 443 | Proxied HTTP and HTTPS |
| | | 81 → 81 | Admin UI (LAN only) |
| Uptime Kuma | `louislam/uptime-kuma` | 3001 → 3001 | Web UI and status pages |
| PeaNUT | `brandawg93/peanut` | 8080 → 8080 | Web UI, API and Prometheus metrics |
| Portainer | `portainer/portainer-ce` | 9443 → 9443 | Web UI (HTTPS) |
| | | 8000 → 8000 | Tunnel for Edge agents (only if Edge agents are used) |

Exact versions and digests will be in [`compose.yaml`](../compose.yaml).

## Volumes and mounts

| Container path | Host source | Service |
| --- | --- | --- |
| `/data` | `APPDATA_ROOT/npm/data` | Nginx Proxy Manager: settings database, proxy host configuration, logs |
| `/etc/letsencrypt` | `APPDATA_ROOT/npm/letsencrypt` | Nginx Proxy Manager: TLS certificates and their private keys |
| `/app/data` | `APPDATA_ROOT/uptime-kuma` | Uptime Kuma: database |
| `/config` | `APPDATA_ROOT/peanut` | PeaNUT: settings, including the NUT server's address and login |
| `/data` | `APPDATA_ROOT/portainer` | Portainer: database, users, environments |
| `/var/run/docker.sock` | the Docker socket | Portainer (an allowed exception, see below) |

Whether each one is a bind mount under `APPDATA_ROOT` or a named volume is settled when the existing data on the
host is adopted; the backup scripts handle both.

## Labels

| Label | Meaning |
| --- | --- |
| `org.honeybeartech.ares.allow.<rule>` | Lets one service break one policy rule; the value is the reason, and must not be empty. Rules: `image`, `digest`, `latest`, `build`, `privileged`, `cap-add`, `host-network`, `host-pid`, `docker-socket`, `healthcheck` ([security.md](security.md#policy)). Agreed: Portainer (`docker-socket`). |

## Commands

| Command | Does |
| --- | --- |
| `docker compose up -d` / `down` / `ps` / `logs <service>` | Runs and inspects the stack |
| `make check` | `docker compose config --format json \| python scripts/check_compose.py`: the policy check |
| `python scripts/check_compose.py [FILE] [--sbom OUT]` | Checks a resolved Compose config (from `FILE` or stdin); `--sbom` also writes a CycloneDX 1.6 SBOM of the images. Exit 0 = no violations, 1 = violations (one line each), 2 = unreadable input |
| `make test`, `make lint` | The checker's tests and the linters |
| `scripts/backup.sh [DIR]` | Stops the stack, archives every service's data mounts (every read-write volume or bind mount except the Docker socket and anonymous volumes), `.env` and any `<service>.env` into `DIR` (default `backups/<date>-<time>`, gitignored) with a `MANIFEST` and `SHA256SUMS`, all mode `600`, then starts what was running. Exit 0 = backup complete |
| `scripts/restore.sh [--yes] DIR [SERVICE...]` | Verifies `DIR/SHA256SUMS`, checks the `MANIFEST`, creates missing containers and volumes, asks for confirmation (unless `--yes`), stops the services, replaces the contents of each listed mount with its archive (owners and modes kept), and starts what was running. Writes only mounts the service still has read-write; never the Docker socket |
| `make smoke` | `scripts/smoke-test.sh`: starts every service under a separate Compose project with throwaway directories and volumes, no fixed container names, no published ports and no env files, waits until all are healthy, round-trips a backup and restore over every data mount, then removes what it created. Exit 0 = all healthy and restored (or no `compose.yaml` yet) |

## Outbound connections

From the host: the image registries (Docker Hub) on `docker compose pull`. From the services: Nginx Proxy
Manager to the backends it proxies and to Let's Encrypt; Uptime Kuma to what it monitors and to its notification
channels; PeaNUT to the NUT server; Portainer to the agents on the other Docker hosts.

## Release files

Each GitHub Release will have `homelab-ares-<version>.tar.gz` (source, with `LICENSE`),
`homelab-ares-<version>.cdx.json` (CycloneDX SBOM of the pinned images), `SHA256SUMS` and its Sigstore
bundle, and SLSA provenance ([verifying-releases.md](verifying-releases.md)).
