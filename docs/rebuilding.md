# Rebuilding the host

How to bring the stack back on a new or wiped machine from a backup made by `scripts/backup.sh`
([upgrading.md](upgrading.md#backing-up)), with every service's settings, certificates and history as they were.

The backup and restore scripts run end to end in CI on every change (the smoke test backs up the running stack,
changes it, restores it and checks the result).

You need: the backup directory (copied off the old host) and this repository.

## 1. The operating system

Install a 64-bit Linux server; the reference is **Debian 13 on arm64**. Then:

```sh
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y unattended-upgrades git
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

## 3. The repository and settings

```sh
git clone https://github.com/HoneyBearTech/homelab-ares.git && cd homelab-ares
git checkout vX.Y.Z      # the release the backup was taken with, or newer; verify it (verifying-releases.md)
cp /path/to/backup/env/.env .env && chmod 600 .env
```

Copy any `<service>.env` from the backup's `env/` (such as `autoheal.env`) the same way (mode `600`). Edit `.env`
if the new host's paths differ; keep the volume names, since the restore creates volumes under them. Create the
data directories as your user and the proxy's network:

```sh
. ./.env && mkdir -p "$NPM_DATA_PATH" "$NPM_LETSENCRYPT_PATH" "$PEANUT_CONFIG_PATH"
docker network create "$PROXY_NETWORK"
docker compose config --quiet && docker compose pull
```

The network gets a new address range; if the proxy's access lists allow its gateway address, update them after
the restore.

## 4. Restore and start

```sh
scripts/restore.sh /path/to/backup    # verifies SHA256SUMS, creates the volumes and containers, asks first
docker compose up -d --wait           # waits until every service reports healthy
docker compose ps
```

Then sign in to each service: Nginx Proxy Manager should list its proxy hosts and certificates, Uptime Kuma its
monitors, Portainer its environments (the agents reconnect on their own if the address is unchanged), and PeaNUT
should show the UPS.

## What the backup doesn't bring back

- **Host settings**: the static address, firewall rules, SSH keys, monitoring agents.
- **Other machines' view of this one**: DNS records, the router's port forwards, anything that reaches Ares by
  address.
- **Services from other projects** on the same host (metrics and logs): restore them from their own backups.
