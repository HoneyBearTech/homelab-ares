# homelab-ares

[![CI](https://github.com/HoneyBearTech/homelab-ares/actions/workflows/ci.yml/badge.svg)](https://github.com/HoneyBearTech/homelab-ares/actions/workflows/ci.yml)
[![CodeQL](https://github.com/HoneyBearTech/homelab-ares/actions/workflows/codeql.yml/badge.svg)](https://github.com/HoneyBearTech/homelab-ares/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/HoneyBearTech/homelab-ares/badge)](https://scorecard.dev/viewer/?uri=github.com/HoneyBearTech/homelab-ares)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/15288/badge)](https://www.bestpractices.dev/projects/15288)
[![OpenSSF Baseline](https://www.bestpractices.dev/projects/15288/baseline)](https://www.bestpractices.dev/projects/15288)

Docker Compose stack for Ares, a homelab Debian 13 (arm64) server. Version-pinned, self-hosted services, kept as code for easy upgrades and rebuilds.

> [!WARNING]
> Ares runs the reverse proxy in front of every other service in a homelab and the Portainer server that can
> control every Docker host it manages. A broken upgrade takes all of them offline, and an upgrade can migrate a
> service's data irreversibly. Back up before every upgrade ([docs/upgrading.md](docs/upgrading.md)).

## Documentation

- [Quick start](docs/quick-start.md): getting the stack running on a fresh Docker host
- [Installing](docs/installing.md): host preparation, where data lives, running it securely, uninstalling
- [Upgrading](docs/upgrading.md): moving to a new release, backup and restore, rolling back
- [Rebuilding](docs/rebuilding.md): a new or wiped host, from a backup
- [Architecture](docs/architecture.md): the services, actors, data flow and how updates reach the host
- [Interfaces](docs/interfaces.md): every setting, port, volume, label and command
- [Verifying releases](docs/verifying-releases.md): checking signatures, checksums, provenance and the SBOM
- [Security requirements](docs/security.md): what the stack protects, what it doesn't, where secrets live
- [Assurance case](docs/assurance-case.md): threat model, trust boundaries, secure design, common weaknesses
- [Dependencies](docs/dependencies.md): how images and tools are chosen, pinned, tracked and patched
- [Roadmap](docs/roadmap.md): the next year, and what homelab-ares will not do
- Project policies: [CONTRIBUTING](CONTRIBUTING.md) · [SECURITY](SECURITY.md) · [GOVERNANCE](GOVERNANCE.md) ·
  [SUPPORT](SUPPORT.md) · [CODE OF CONDUCT](CODE_OF_CONDUCT.md) · [CHANGELOG](CHANGELOG.md)

## What's in the stack

([architecture](docs/architecture.md), ports in [interfaces](docs/interfaces.md#services-and-ports)):

- **Nginx Proxy Manager**: the reverse proxy and TLS certificates for the homelab's web services
- **Uptime Kuma**: uptime checks and status pages
- **PeaNUT**: a dashboard and metrics endpoint for the UPS, through a NUT server
- **Portainer**: a web UI for the Docker hosts in the homelab (server; the hosts run its agent)
- **autoheal**: restarts any of them whose health check fails, through a socket proxy that only lets it list,
  inspect, restart and stop containers

Every service has a health check, and every image is pinned by tag **and** digest, for `linux/arm64`. New versions arrive as Dependabot pull
requests that CI checks and the maintainer merges; nothing on the host updates itself. Metrics dashboards
(Grafana, Prometheus) are a separate project and not part of this stack.

## Getting started

```sh
git clone https://github.com/HoneyBearTech/homelab-ares.git && cd homelab-ares
cp .env.example .env && chmod 600 .env              # then set TZ, and the paths if you keep data elsewhere
. ./.env && mkdir -p "$NPM_DATA_PATH" "$NPM_LETSENCRYPT_PATH" "$PEANUT_CONFIG_PATH"
docker network create "$PROXY_NETWORK"
docker compose up -d --wait
```

The full steps are in the [quick start](docs/quick-start.md).

## Usage

```sh
docker compose ps                 # what's running
docker compose logs -f <service>  # one service's log
make check                        # policy check: every image pinned, nothing privileged
scripts/backup.sh                 # back up every service's data (stops the stack briefly)
```

Upgrading to a new release: [docs/upgrading.md](docs/upgrading.md).

## Configuration

Settings come from `.env` (template [`.env.example`](.env.example)), which holds no secrets.

| Setting | Default in `.env.example` | Meaning |
| --- | --- | --- |
| `TZ` | `Etc/UTC` | Time zone |
| `NPM_DATA_PATH` | `/srv/appdata/npm/data` | Nginx Proxy Manager's settings, proxy hosts and logs |
| `NPM_LETSENCRYPT_PATH` | `/srv/appdata/npm/letsencrypt` | Nginx Proxy Manager's certificates and private keys |
| `PROXY_NETWORK` | `homelab-ares_proxy` | The proxy's Docker network, created once outside the stack |
| `UPTIME_KUMA_VOLUME` | `homelab-ares_uptime-kuma` | Docker volume with Uptime Kuma's database |
| `PEANUT_CONFIG_PATH` | `/srv/appdata/peanut` | PeaNUT's settings, including the NUT login |
| `PORTAINER_VOLUME` | `homelab-ares_portainer` | Docker volume with Portainer's database |

All of it holds certificates and logins: back it up (`scripts/backup.sh`). autoheal's optional webhook URL (restart
notices, for example to Discord) goes in `autoheal.env` (template [`autoheal.env.example`](autoheal.env.example),
mode `600`, gitignored).

Ports, volumes and labels: [docs/interfaces.md](docs/interfaces.md).

## Running it securely

- Keep the admin UIs (Nginx Proxy Manager's, Portainer's, Uptime Kuma's) on your LAN with strong passwords;
  publish only the proxy's HTTP and HTTPS ports beyond it. Docker-published ports bypass host firewalls such
  as `ufw`.
- Portainer's server mounts the Docker socket, which is root on the host, and controls every agent that is
  paired with it: treat its login like a root password. autoheal never gets the socket: it goes through a proxy
  that only lets it list, inspect, restart and stop containers.
- Secrets (logins, API tokens, TLS private keys, the NUT login) live only in each service's data, never in this
  repository or `.env`. Backups contain them: keep them private and off the host.
- Don't run an auto-updater such as Watchtower on these containers; upgrade by release instead.
- The policy check refuses privileged containers, added capabilities, host networking and Docker socket
  mounts unless a service documents why ([docs/security.md](docs/security.md)).

Report vulnerabilities privately: [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
