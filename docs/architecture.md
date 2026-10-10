# Architecture

homelab-ares is the Docker Compose definition of **Ares**, a homelab's edge and monitoring server: the reverse
proxy that every other web service is reached through, the uptime checks, the UPS dashboard and the Docker
management UI. Ares is a small bare-metal arm64 machine (Debian 13), so it keeps running when the virtualisation
hosts don't. The repository holds configuration, not application code: the services run from their upstream
images, pinned by digest.

## Services

| Service | Image source | Role |
| --- | --- | --- |
| Nginx Proxy Manager | the project's own image | Reverse proxy for the homelab's web services: one HTTPS name per service, TLS certificates (Let's Encrypt), access lists |
| Uptime Kuma | the project's own image | Uptime checks of hosts and services, with notifications and status pages |
| PeaNUT | the project's own image | Dashboard for the UPS, read from a NUT server on the network; also exposes the UPS readings as Prometheus metrics |
| Portainer (server) | the project's own image (Community Edition, Alpine variant) | Web UI for the Docker hosts in the homelab: Ares itself through the Docker socket, the others through the Portainer agent running on each of them |
| autoheal | the project's own image | Restarts any service whose health check fails, and can post a notice to a webhook (Docker on its own only restarts a container that exits) |
| socket-proxy | linuxserver.io | Gives autoheal a filtered view of the Docker API (list, inspect, restart and stop containers only) on an internal network |

Every service has a health check, so `docker compose ps` shows a broken one, and autoheal restarts it.

Metrics and logs (Grafana, Prometheus, Loki) also run on Ares, but from their own project and repository; this
stack doesn't include or manage them.

## Actors and actions

| Actor | Does |
| --- | --- |
| Maintainer | Merges pull requests, tags releases, runs `git pull` / `docker compose up -d` on the host, configures each service in its web UI |
| Dependabot | Opens a pull request when an image (tag and digest), a check tool or an Action has a new version; patch and minor updates are auto-merged once the checks pass |
| CI | Lints, scans for secrets, tests the checker, resolves the Compose file, enforces the policy and smoke-tests the stack on arm64 on every pull request |
| Release workflow | On a version tag: checks the policy, writes the SBOM, signs the checksums, publishes the GitHub Release |
| LAN and remote users | Reach the homelab's web services through Nginx Proxy Manager; use the admin UIs from the LAN, behind each service's own login |
| Let's Encrypt | Issues and renews the proxy's certificates (ACME) |
| The services | Nginx Proxy Manager forwards requests to backends on other hosts; Uptime Kuma probes hosts and services; PeaNUT polls the NUT server; Portainer talks to the local Docker socket and to the agents on other hosts |

## Data flow

```
clients ──HTTPS──▶ Nginx Proxy Manager ──HTTP(S)──▶ web services on the homelab's hosts
                          │
                          └──ACME──▶ Let's Encrypt (certificate issue and renewal)

Uptime Kuma ──ping / HTTP──▶ hosts and services ──▶ notifications
PeaNUT ──NUT protocol──▶ NUT server (UPS) ; monitoring ──scrape──▶ PeaNUT metrics
Portainer ──Docker socket──▶ Docker on Ares ; Portainer ──agent API──▶ Docker on the other hosts
autoheal ──(internal network)──▶ socket-proxy ──read-only socket, filtered──▶ Docker on Ares (restart unhealthy)
```

Each service keeps its settings and database in its own data directory or volume (see
[interfaces.md](interfaces.md#volumes-and-mounts)), which is what `scripts/backup.sh` archives.

## How changes reach the host

1. Dependabot (or the maintainer) opens a pull request that changes an image's tag and digest.
2. CI resolves the Compose file, runs the policy check and the smoke test; the maintainer reads the service's
   release notes.
3. The pull request is squash-merged (automatically for Dependabot's patch and minor updates, once every
   check passes); a version tag makes a signed release.
4. On the host: back up, `git checkout <tag>`, `docker compose pull && docker compose up -d`
   ([upgrading.md](upgrading.md)).

Nothing on the host updates itself: a version that runs is always a version that's in git.

## Repository layout

| Path | What |
| --- | --- |
| `compose.yaml` | The stack |
| `.env.example`, `autoheal.env.example` | Templates for the settings and autoheal's optional webhook |
| `scripts/check_compose.py` | The policy check and SBOM generator (standard-library Python) |
| `scripts/backup.sh`, `scripts/restore.sh` | Backup and restore of every service's data |
| `scripts/scheduled-backup.sh`, `deploy/systemd/` | Nightly backup, copied off the host with rsync and pruned, reported to an Uptime Kuma push monitor |
| `scripts/smoke-test.sh` | Starts the stack in isolation, waits for health, and round-trips a backup |
| `tests/` | The checker's tests, with JSON fixtures |
| `docs/` | This documentation |
| `.github/` | CI, release and security workflows, Dependabot, templates |
| `.gitlab-ci.yml` | The pipeline of the copy on the maintainer's GitLab: mirrors GitHub, re-runs the daemon-free checks |
