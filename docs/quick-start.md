# Quick start

> **Planned:** `compose.yaml` isn't in the repository yet, so step 4 has nothing to start. The steps are the
> ones the stack will use.

You need a Linux host on arm64 or amd64 (the reference is Debian 13 on arm64) with Docker Engine and the
Compose v2 plugin, and a user in the `docker` group. Ports 80 and 443 must be free for the proxy.

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

   In `.env`, set `TZ` and `APPDATA_ROOT` (where the services keep their data). Every setting is described in
   [interfaces.md](interfaces.md#settings).

3. **Create the data directory** as your user, so Docker doesn't create it owned by root:

   ```sh
   . ./.env && mkdir -p "$APPDATA_ROOT"
   ```

4. **Check and start.**

   ```sh
   docker compose config --quiet   # the file resolves with your settings
   docker compose up -d --wait     # waits until every service reports healthy
   docker compose ps
   ```

5. **Finish each service's setup in its web UI** (ports in [interfaces.md](interfaces.md#services-and-ports)),
   starting with its admin login: Nginx Proxy Manager (admin port 81) asks you to change its default login on
   first sign-in, Uptime Kuma and Portainer ask you to create one. Point PeaNUT at your NUT server in its
   settings.

To upgrade later, follow [upgrading.md](upgrading.md); it starts with a backup.
