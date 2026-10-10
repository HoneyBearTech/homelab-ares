# Rebuilding the host

How to bring the stack back on a new or wiped machine from a backup made by `scripts/backup.sh` (by hand,
[upgrading.md](upgrading.md#backing-up), or nightly, [installing.md](installing.md#scheduled-backups)), with every
service's settings, certificates and history as they were, and with the proxy's network on the same address range,
so access lists that allow its gateway keep working.

The backup and restore scripts run end to end in CI on every change: the smoke test backs up the running stack,
changes it, restores it and checks the result, and copies a scheduled backup to a stand-in backup server.
[Rehearse](#rehearsing-a-rebuild) the steps below on a scratch machine before you need them.

You need: a backup (copied off the old host, or on the backup server), this repository, and a 64-bit machine;
the reference is **Debian 13 on arm64**.

## 1. The operating system

Install a 64-bit Linux server. Then:

```sh
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y unattended-upgrades git rsync curl
```

Give the machine the same address the old one had (or update everything that reaches it by address: DNS
records, port forwards for 80 and 443, the Portainer agents' allowed server, monitoring).

## 2. Docker

Install Docker Engine and the Compose plugin from Docker's own repository, following
[docs.docker.com/engine/install/debian](https://docs.docker.com/engine/install/debian/) (Docker Engine 25 or
later, Compose 2.24 or later). Add your user to the `docker` group, which is equivalent to root on the host, and
log in again:

```sh
sudo usermod -aG docker "$USER"
```

Don't install an auto-updater such as Watchtower ([installing.md](installing.md#running-it-securely)).

## 3. The backup

From the backup server: the old host's key went with it, so create a new one and an SSH alias as in
[installing.md](installing.md#scheduled-backups) step 2, and add the public key to the backup user's
`~/.ssh/authorized_keys` on the server. Then list the backups (named `<date>-<time>`) and copy the newest:

```sh
rsync --list-only backup-host:/volume1/<folder>/
rsync -rlpt backup-host:/volume1/<folder>/<date>-<time>/ ~/restore/
```

Check it before using it. A copy that was cut off has no `SHA256SUMS` (it's sent last): take the one before.

```sh
cd ~/restore && sha256sum -c --quiet SHA256SUMS && cd -
cat ~/restore/VERSION      # the release (or commit) the old host ran
cat ~/restore/NETWORKS     # the proxy's network: name, address range, gateway
```

Keep `~/restore` private: it holds every login and private key. Backups made before `VERSION` and `NETWORKS`
existed lack them; the stack still restores, but the proxy's network gets a new address range (step 4).

## 4. The repository and settings

```sh
git clone https://github.com/HoneyBearTech/homelab-ares.git && cd homelab-ares
git checkout vX.Y.Z      # the release in VERSION, or newer; verify it (verifying-releases.md)
cp ~/restore/env/.env .env && chmod 600 .env
```

Copy any other file from the backup's `env/` (such as `autoheal.env` and `backup.env`) the same way (mode `600`).
Edit `.env` if the new host's paths differ; keep the volume names, since the restore creates volumes under them.
Create the data directories as your user:

```sh
. ./.env && mkdir -p "$NPM_DATA_PATH" "$NPM_LETSENCRYPT_PATH" "$PEANUT_CONFIG_PATH"
sudo chown 1000:1000 "$PEANUT_CONFIG_PATH"   # PeaNUT runs as uid 1000
```

Create the proxy's network with the address range it had, from the backup's `NETWORKS`:

```sh
grep -v '^#' ~/restore/NETWORKS | while IFS=$'\t' read -r name subnet gateway; do
  docker network create --subnet "$subnet" --gateway "$gateway" "$name"
done
docker network inspect "$PROXY_NETWORK" --format '{{range .IPAM.Config}}{{.Subnet}} {{.Gateway}}{{end}}'
```

If the backup has no `NETWORKS`, `docker network create "$PROXY_NETWORK"` instead, and after the restore update
every proxy access list that allowed the old network's gateway. If the range is already taken on the new host by
another network, remove or move that one first. Then:

```sh
docker compose config --quiet && docker compose pull
```

## 5. Restore and start

```sh
scripts/restore.sh ~/restore          # verifies SHA256SUMS, creates the volumes and containers, asks first
docker compose up -d --wait           # waits until every service reports healthy
docker compose ps
```

Then check each service:

- **Nginx Proxy Manager** (port 81): its proxy hosts, certificates and access lists are listed; a proxied site
  opens by its name, from the LAN and, if it's public, from outside.
- **Uptime Kuma** (port 3001): its monitors and notification settings are there, and the monitors turn green.
- **Portainer** (port 9443): every environment shows as up; the agents reconnect on their own if the address is
  unchanged.
- **PeaNUT** (port 8080): it shows the UPS.
- Anything that scrapes this host's metrics (Uptime Kuma's, PeaNUT's) or probes the proxied sites gets answers
  again, with the status codes it got before.

## 6. Scheduled backups again

The settings came back with `backup.env`, and the SSH alias from step 3 still works. Install the timer as in
[installing.md](installing.md#scheduled-backups) step 5, then run `scripts/scheduled-backup.sh` once by hand and
check that it reaches the backup server and the push monitor. Delete `~/restore`.

## What the backup doesn't bring back

- **Host settings**: the static address, firewall rules, SSH keys (including the backup key), monitoring agents.
- **Other machines' view of this one**: DNS records, the router's port forwards, anything that reaches Ares by
  address.
- **Services from other projects** on the same host (metrics and logs): restore them from their own backups.

## Rehearsing a rebuild

Run steps 3 to 5 on a scratch machine now and then, so the first real rebuild isn't the first try, and so you
know how long it takes. Any arm64 machine with Docker will do for those steps: a spare board, a VM, or Docker
Desktop on a Mac with Apple silicon (there, put the data directories under your home directory in `.env`, and
`chmod 777` PeaNUT's instead of the `chown`; macOS checks the backup with `shasum -a 256 -c` instead of
`sha256sum -c`). Use the newest backup, and leave the live host alone.

The restored services believe they are the live ones, so keep them from acting like it:

- **Don't copy `autoheal.env` or `backup.env`, and don't install the timer**: they'd post to your restart channel
  and write to the backup server.
- **Uptime Kuma** starts monitoring at once and notifies like the live one about anything it can't reach from the
  scratch machine. Once you've seen its monitors, pause them all.
- **Portainer** holds the agents' trust, so it can manage every agent host just like the live one. Look, don't
  change anything, and stop it when you're done.
- **Nginx Proxy Manager** answers on the scratch machine's ports 80 and 443, which nothing forwards to. It may try
  to renew certificates that are due; that does no harm.

Note how long each step took and anything this page got wrong or left out, and fix the page in a pull request.
Then remove everything the rehearsal created; it all holds secrets:

```sh
. ./.env && docker compose down
docker volume rm "$UPTIME_KUMA_VOLUME" "$PORTAINER_VOLUME" homelab-ares_npm-logrotate
docker network rm "$PROXY_NETWORK"
sudo rm -rf "$NPM_DATA_PATH" "$NPM_LETSENCRYPT_PATH" "$PEANUT_CONFIG_PATH" ~/restore .env ./*.env
```
