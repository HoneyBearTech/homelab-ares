# Installing

The [quick start](quick-start.md) is the short version of this page.

> **Planned:** `compose.yaml` isn't in the repository yet. The requirements and security advice apply now; the
> install steps apply once the stack is added.

## Requirements

- Linux with Docker Engine and the Compose v2 plugin (Docker Engine 25 or later and Compose 2.24 or later, for
  the health checks' `start_interval`). The reference host is **Debian 13 on arm64**; every image is chosen to
  publish `linux/arm64` and `linux/amd64`.
- A user in the `docker` group to run `docker compose`. Membership is equivalent to root on the host, so keep
  that group small.
- Ports 80 and 443 free and reachable from the clients that use the proxy (and, for Let's Encrypt's HTTP
  challenge, from the internet on port 80).
- Little disk: the services' data is small, but Nginx Proxy Manager's logs grow; watch the free space on small
  boards.

## Where data lives

| What | Where on the host | In the container |
| --- | --- | --- |
| Nginx Proxy Manager's settings, proxy hosts and logs | `APPDATA_ROOT/npm/data` | `/data` |
| Nginx Proxy Manager's certificates and private keys | `APPDATA_ROOT/npm/letsencrypt` | `/etc/letsencrypt` |
| Uptime Kuma's database | `APPDATA_ROOT/uptime-kuma` | `/app/data` |
| PeaNUT's settings (NUT server address and login) | `APPDATA_ROOT/peanut` | `/config` |
| Portainer's database | `APPDATA_ROOT/portainer` | `/data` |

These are **Planned** paths ([interfaces.md](interfaces.md#volumes-and-mounts)).

## Installing

1. Clone the repository (or download a release's source archive and verify it,
   [verifying-releases.md](verifying-releases.md)).
2. Create `.env` from `.env.example` (mode `600`) and set every value.
3. Create `APPDATA_ROOT`, then `docker compose up -d`.

**Adopting existing containers.** If the services already run on the host (from Portainer stacks or another
Compose project), point the stack at their existing data instead of starting empty: stop the old containers,
make sure each data directory or volume is where [interfaces.md](interfaces.md#volumes-and-mounts) expects it
(or set `APPDATA_ROOT` accordingly), and keep the same published ports, so nothing that reaches them has to
change. Take a backup of the old data first. Be especially careful with the proxy: while it's down, every
service behind it is unreachable.

Running `main` instead of a release is possible but unsupported for anything you depend on.

## Running it securely

- **Admin UIs on the LAN only.** Nginx Proxy Manager's admin port (81), Portainer (9443) and Uptime Kuma (3001)
  must not be reachable from the internet; only the proxy's 80 and 443 should be. Docker-published ports bypass
  host firewalls such as `ufw`, so restrict them at the router or with Docker's own `DOCKER-USER` rules.
- **Change every default login at once.** Nginx Proxy Manager starts with a well-known default admin login;
  change it before anything else. Use long, unique passwords and turn on two-factor authentication where the
  service offers it.
- **Portainer is root on this host and controls every paired agent.** Anyone with its admin login can run any
  container, with any mounts, on every Docker host it manages. Give it the strongest password you have, keep it
  on the LAN and keep it updated.
- **Proxy access lists.** Use Nginx Proxy Manager's access lists to keep LAN-only services LAN-only, even though
  they have a public name.
- Keep `.env` at mode `600`; it holds no secrets by design, but it describes your host.
- Back up `APPDATA_ROOT`: it holds the certificates' private keys and every login
  ([upgrading.md](upgrading.md#backing-up)).
- Don't add services that mount the Docker socket, run privileged or use the host network without a documented
  reason; the policy check refuses them ([security.md](security.md)).
- Don't run an auto-updater (such as Watchtower) on these containers: it would replace the pinned, reviewed
  versions with whatever a tag points to today.

## Uninstalling

```sh
docker compose down          # stops and removes the containers and the stack's network
```

`APPDATA_ROOT` and any named volumes are left untouched. Remove them by hand if you no longer want the services'
data; note that it contains private keys and passwords.
