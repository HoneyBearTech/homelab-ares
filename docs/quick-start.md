# Quick start

You need a Linux host on arm64 or amd64 (the reference is Debian 13 on arm64) with Docker Engine 25 or later and
the Compose v2 plugin (2.24 or later), and a user in the `docker` group. Ports 80 and 443 must be free for the
proxy.

1. **Get the stack.**

   ```sh
   git clone https://github.com/HoneyBearTech/homelab-ares.git && cd homelab-ares
   ```

   Once releases exist, check out the latest one (`git checkout vX.Y.Z`) and verify it first
   ([verifying-releases.md](verifying-releases.md)).

2. **Configure it.**

   ```sh
   cp .env.example .env && chmod 600 .env
   ```

   The defaults work for a new installation; set `TZ`, and change the paths if you keep data elsewhere. Every
   setting is described in [interfaces.md](interfaces.md#settings). For restart notices from autoheal, also
   create `autoheal.env` from `autoheal.env.example` (mode `600`) with a webhook URL.

3. **Create the data directories and the proxy's network** (the directories as your user, so Docker doesn't
   create them owned by root):

   ```sh
   . ./.env && mkdir -p "$NPM_DATA_PATH" "$NPM_LETSENCRYPT_PATH" "$PEANUT_CONFIG_PATH"
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
   first sign-in, Uptime Kuma and Portainer ask you to create one (Portainer only for the first few minutes after
   it starts). Point PeaNUT at your NUT server in its settings.

To upgrade later, follow [upgrading.md](upgrading.md); it starts with a backup.
