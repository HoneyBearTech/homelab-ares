# Installing

The [quick start](quick-start.md) is the short version of this page.

## Requirements

- Linux with Docker Engine and the Compose v2 plugin (Docker Engine 25 or later and Compose 2.24 or later, for
  the health checks' `start_interval`). The reference host is **Debian 13 on arm64**; every image is chosen to
  publish `linux/arm64` and `linux/amd64`.
- A user in the `docker` group to run `docker compose`. Membership is equivalent to root on the host, so keep
  that group small.
- Ports 80 and 443 free and reachable from the clients that use the proxy (and, for Let's Encrypt's HTTP
  challenge, from the internet on port 80).
- Little disk: the services' data is small, but Nginx Proxy Manager's logs grow. It rotates them weekly and keeps
  four compressed weeks, so a busy proxy can still write a gigabyte or more in a week; watch the free space on
  small boards.
- `PEANUT_CONFIG_PATH` owned by (or writable for) uid 1000: PeaNUT runs as that user and saves its login there.

## Where data lives

| What | Where on the host (setting) | In the container |
| --- | --- | --- |
| Nginx Proxy Manager's settings, proxy hosts and logs | directory `NPM_DATA_PATH` | `/data` |
| Nginx Proxy Manager's certificates and private keys | directory `NPM_LETSENCRYPT_PATH` | `/etc/letsencrypt` |
| When Nginx Proxy Manager last rotated its logs | volume `homelab-ares_npm-logrotate` (Compose creates it) | `/var/lib/logrotate` |
| Uptime Kuma's database | volume `UPTIME_KUMA_VOLUME` | `/app/data` |
| PeaNUT's settings (NUT server address and login) | directory `PEANUT_CONFIG_PATH` | `/config` |
| Portainer's database | volume `PORTAINER_VOLUME` | `/data` |

Details in [interfaces.md](interfaces.md#volumes-and-mounts).

## Installing

1. Clone the repository (or download a release's source archive and verify it,
   [verifying-releases.md](verifying-releases.md)).
2. Create `.env` from `.env.example` (mode `600`) and set every value. Optionally create `autoheal.env` from
   `autoheal.env.example` (mode `600`) with a webhook URL for restart notices.
3. Create the data directories and the proxy's network (`docker network create "$PROXY_NETWORK"`), then
   `docker compose up -d --wait`.

### Adopting existing containers

If the services already run on the host (from Portainer stacks, `docker run` or other Compose projects), point
the stack at their existing data instead of starting empty:

- Set each `*_PATH` to the directory the old container mounts, each `*_VOLUME` to the volume it uses
  (`docker inspect <container>` lists both), and `PROXY_NETWORK` to the network the old proxy is on. Keeping the
  proxy's network keeps its address range, which access lists may rely on. Docker Compose warns that the volumes
  "already exist but were not created by Docker Compose"; that's expected.
- The published ports and container names are the services' usual ones; anything that reaches them keeps working.
- Back up the old data first, then stop and remove the old containers (the names must be free) and start the
  stack. Be especially careful with the proxy: while it's down, every service behind it is unreachable.
- A newer image may migrate a service's data on its first start and can't go back; the backup is the way back.
- **Uptime Kuma** runs the slim image, without Chromium: change any "Real Browser" monitor to an HTTP monitor first.
- **PeaNUT 6** asks for a login on first start if its settings have none yet, and its metrics then need that login:
  update whatever scrapes them. Change the owner of its settings directory to uid 1000 first.

Running `main` instead of a release is possible but unsupported for anything you depend on.

## Scheduled backups

`scripts/scheduled-backup.sh` takes a backup (`scripts/backup.sh`), copies it to another machine with rsync, keeps
only the newest few in both places and reports to an Uptime Kuma push monitor. A systemd timer runs it nightly.
Every setting is in the optional `backup.env` ([interfaces.md](interfaces.md#backupenv)). The backups hold every
login and private key: copy them only to a machine you trust as much as this one.

1. **On the backup server**, create a folder for the backups and a user that can write only there and use rsync
   over SSH (on a Synology: a shared folder, a non-admin user with read/write on that folder only, rsync allowed
   under Application Privileges, SSH on, the rsync service on under File Services, and the user home service on so
   the user can have an `authorized_keys`). Whoever controls this host can delete or overwrite what it copied
   there, so keep older versions where the backup user can't reach them: snapshots of the folder, or a versioned
   copy of it made on the server after the nightly backup (on a Synology without Btrfs, a Hyper Backup task with
   rotation, into a folder the backup user has no access to). A recycle bin isn't enough: Synology's doesn't keep
   files deleted over rsync.
2. **On this host**, as the user who runs the stack, install rsync and curl, and create a key used only for the
   backups, with an alias for it in `~/.ssh/config`:

   ```sh
   sudo apt install -y rsync curl
   ssh-keygen -t ed25519 -N '' -f ~/.ssh/homelab-ares-backup
   ```

   ```text
   Host backup-host
     HostName <the backup server's address>
     User <the backup user>
     IdentityFile ~/.ssh/homelab-ares-backup
     IdentitiesOnly yes
   ```

   Add the public key to the backup user's `~/.ssh/authorized_keys` on the server, prefixed with
   `restrict,from="<this host's address>"` (no shell or forwarding, and only from this host), then check that
   `rsync --list-only backup-host:/volume1/<folder>/` works without a password prompt.
3. **Settings**: `cp backup.env.example backup.env && chmod 600 backup.env`, then set
   `BACKUP_REMOTE=backup-host:/volume1/<folder>` and, optionally, the retention and `BACKUP_PING_URL`. For the
   ping, add a monitor of type **Push** in Uptime Kuma with a heartbeat interval of 25 hours, and copy its URL.
4. **Try it**: `scripts/scheduled-backup.sh`. Each service stops only while its own data is archived, so the proxy
   is down for seconds, not for the whole backup.
5. **Schedule it**, with the systemd user units in [`deploy/systemd/`](../deploy/systemd/) (they expect the
   checkout at `~/homelab-ares`; edit both paths in the `.service` file if it's elsewhere). Lingering lets the
   timer run while you're logged out:

   ```sh
   mkdir -p ~/.config/systemd/user
   cp deploy/systemd/homelab-ares-backup.* ~/.config/systemd/user/
   sudo loginctl enable-linger "$USER"
   systemctl --user daemon-reload
   systemctl --user enable --now homelab-ares-backup.timer
   systemctl --user list-timers homelab-ares-backup.timer     # next run: 04:30, plus up to 10 minutes
   journalctl --user -u homelab-ares-backup                   # what the last runs did
   ```

Restore a copy from the backup server as [rebuilding.md](rebuilding.md) describes; `scripts/restore.sh` verifies
its `SHA256SUMS` first, and a copy that was cut off has none yet, so it is refused.

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
- Keep `autoheal.env` at mode `600`: it holds the webhook URL.
- autoheal never gets the Docker socket: it goes through `socket-proxy`, which only lets it list, inspect,
  restart and stop containers, on an internal network.
- Back up the services' data (`scripts/backup.sh`), and schedule it with a copy off the host
  ([Scheduled backups](#scheduled-backups)): it holds the certificates' private keys and every login.
- Keep `backup.env` at mode `600`: it holds the push monitor's URL. The backup key in `~/.ssh` should open only the
  backup user's account on the backup server, and that account should reach only the backup folder.
- Don't add services that mount the Docker socket, run privileged or use the host network without a documented
  reason; the policy check refuses them ([security.md](security.md)).
- Don't run an auto-updater (such as Watchtower) on these containers: it would replace the pinned, reviewed
  versions with whatever a tag points to today.

## Uninstalling

```sh
docker compose down          # stops and removes the containers and the stack's network
```

The data directories, the volumes and the proxy's network are left untouched. Remove them by hand
(`docker volume rm`, `docker network rm`) if you no longer want the services' data; note that it contains private
keys and passwords.
