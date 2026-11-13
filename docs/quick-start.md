# Quick start

You need a Linux host on arm64 or amd64 (the reference is Debian 13 on arm64) with Docker Engine 25 or later and
the Compose v2 plugin (2.24 or later), and a user in the `docker` group. Ports 80, 443, 81, 3001, 8080 and 9443
must be free; ports 80 and 443 must also be reachable from the proxy's clients (and from the internet on port 80
for Let's Encrypt's HTTP challenge).

1. **Get the stack.**

   ```sh
   git clone https://github.com/HoneyBearTech/homelab-ares.git && cd homelab-ares
   ```

   Check out the latest release (`git checkout vX.Y.Z`) and verify it first
   ([verifying-releases.md](verifying-releases.md)), or stay on `main` the way the maintainer's server does
   ([upgrading.md](upgrading.md#following-main)).

2. **Configure it.**

   ```sh
   cp .env.example .env && chmod 600 .env
   ```

   The defaults work for a new installation; set `TZ`, and `CONFIG_ROOT` if you keep the data elsewhere (never
   inside `/var/lib/docker/volumes`: [installing.md](installing.md#where-data-lives)). Every setting is described in
   [interfaces.md](interfaces.md#settings). For restart notices from autoheal, also
   create `autoheal.env` from `autoheal.env.example` (mode `600`) with a webhook URL. Optional webhook and backup
   secrets belong in the ignored `autoheal.env` and `backup.env` files, using their templates, rather than `.env`.

3. **Create the data directories and the proxy's network.** Source only a trusted local `.env` into the current
   shell. Creating directories under `CONFIG_ROOT` requires write permission; `sudo` supports the default location
   on a fresh host. New directories are owned by root; change ownership only for PeaNUT, which runs as uid 1000:

   ```sh
   . ./.env && sudo mkdir -p "$CONFIG_ROOT/npm/config" "$CONFIG_ROOT/npm/letsencrypt" \
     "$CONFIG_ROOT/npm/logrotate" "$CONFIG_ROOT/uptime-kuma/config" \
     "$CONFIG_ROOT/peanut/config" "$CONFIG_ROOT/portainer/config"
   sudo chown 1000:1000 "$CONFIG_ROOT/peanut/config"   # PeaNUT runs as uid 1000
   docker network create "$PROXY_NETWORK"
   ```

4. **Check and start.**

   ```sh
   docker compose config --quiet   # the file resolves with your settings
   docker compose up -d --wait     # waits until every service reports healthy
   docker compose ps
   ```

5. **Finish each service's setup in its web UI** (ports in [interfaces.md](interfaces.md#services-and-ports)),
   starting with its admin login: Nginx Proxy Manager (admin port 81) asks you to change its default login on
   first sign-in, Uptime Kuma, PeaNUT and Portainer ask you to create one (Portainer only for the first few minutes
   after it starts). Point PeaNUT at your externally supplied NUT server in its settings; this stack does not run
   a NUT server. If a monitoring system scrapes PeaNUT's metrics, give it PeaNUT's login (HTTP Basic auth).

To upgrade later, follow [upgrading.md](upgrading.md); it starts with a backup.
