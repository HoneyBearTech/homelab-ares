# Changelog

All notable changes to homelab-ares are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- [docs/rebuilding.md](docs/rebuilding.md#rehearsing-a-rebuild), from the first rehearsal: clear clashing container
  names, ports and the proxy's address range on the scratch machine first; relay the copy through the live host;
  pause Uptime Kuma's monitors before its first start (no false alerts); check sites behind an access list from
  the proxy network's gateway on Docker Desktop; services that trust the proxy by address (Home Assistant's
  `trusted_proxies`) are listed under what a backup doesn't bring back.

### Added

- `.gitlab-ci.yml` for the copy of the repository on the maintainer's self-hosted GitLab. GitHub stays the
  project's home and its Actions the required checks; on GitLab a scheduled job mirrors `main` and the tags from
  GitHub (fast-forward only, with a project access token in a masked, protected CI/CD variable), and every
  commit that arrives gets the checks that need no Docker daemon: ruff, yamllint, shellcheck, the unit tests
  with the coverage floor, gitleaks over the whole history, actionlint and the Compose policy check.

## [0.2.5] - 2026-10-10

### Fixed

- Nginx Proxy Manager rotates its logs weekly again after an upgrade. logrotate's record of the last rotation
  lived in the container, so each new container started the week again and the logs kept growing. It now lives
  in the volume `homelab-ares_npm-logrotate`, which Compose creates on the first `docker compose up`; there is no
  new setting.

## [0.2.4] - 2026-10-09

### Changed

- Portainer CE 2.45.2, the current long-term-support release (from 2.39.8). Its agents on other hosts move to 2.45.2
  at the same time ([docs/upgrading.md](docs/upgrading.md#portainer-and-its-agents)). Portainer migrates its database
  on the first start, one way: back up first.

## [0.2.3] - 2026-10-09

**Correction (2026-10-10):** the `v0.2.3` tag points at a commit that also contains the Portainer 2.45.2 update
released as 0.2.4: its `compose.yaml` and docs are the same as 0.2.4's, only this changelog differs. Deploying 0.2.3
upgrades Portainer from 2.39.8 to 2.45.2 and migrates its database, one way; read 0.2.4's notes first, and prefer
0.2.4. The release's signatures and provenance are valid; the tag can't be moved.

### Fixed

- The scheduled backup's report to Uptime Kuma is retried for two minutes instead of 25 seconds. When the push
  monitor is this stack's own Uptime Kuma, the backup has just restarted it, and the report failed with 502 until
  it was answering again.

## [0.2.2] - 2026-10-09

### Added

- Label `org.honeybeartech.ares.backup.exclude`: container paths, each directly inside one of the service's data
  mounts, that `scripts/backup.sh` leaves out and `scripts/restore.sh` leaves as they are. The smoke test checks
  both.

### Changed

- Backups leave out Nginx Proxy Manager's logs (`/data/logs`). They grow without limit (hundreds of megabytes on a
  long-running proxy), aren't needed to rebuild it, and kept the proxy down for half a minute or more while they
  were archived; now it's down for seconds. A restore keeps the current logs.

## [0.2.1] - 2026-10-09

### Fixed

- PeaNUT saves its login in its settings directory (`AUTH_FILE_PATH=/config/auth.yaml`). PeaNUT 6.0.0 saves it
  inside the container instead, where the read-only root filesystem stops it: the login created on the setup page
  was never saved, and signing in failed. Fixed upstream but not released yet. The smoke test checks it.

## [0.2.0] - 2026-10-09

Hardened services, nightly backups copied off the host, and a rebuild guide that recreates the proxy's network as
it was.

### Upgrading

- Every service now runs without Linux capabilities (except the few Nginx Proxy Manager and Uptime Kuma add back)
  and with a read-only root filesystem. Data adopted from another installation must be owned as each image
  expects: Portainer's volume by root, PeaNUT's settings directory by uid 1000. A service that fails with
  "permission denied" on its first start usually has data with an unexpected owner.

### Added

- Scheduled backups: `scripts/scheduled-backup.sh` takes a backup, copies it off the host with rsync, keeps the
  newest few here and there, and reports to an Uptime Kuma push monitor. Settings in the optional, gitignored
  `backup.env` (template `backup.env.example`); systemd user units in `deploy/systemd/` run it nightly
  (docs/installing.md#scheduled-backups). The smoke test runs it against a stand-in backup server.

### Changed

- Each backup also records `NETWORKS`, the address range and gateway of every network the stack uses but doesn't
  create (the proxy's), and `VERSION`, the checkout's `git describe`, so a rebuilt host can recreate the proxy's
  network as it was. The smoke test checks both.
- docs/rebuilding.md: fetching the newest complete backup from the backup server, recreating the proxy's network
  from `NETWORKS`, what to check after the restore, and how to rehearse a rebuild on a scratch machine without
  disturbing the live host.
- `scripts/backup.sh` stops one service at a time, only while its own data is archived, instead of the whole stack;
  services with nothing to archive (autoheal, socket-proxy) keep running. The proxy is down for seconds.
- docs/installing.md#scheduled-backups: older backups need snapshots or a versioned copy on the backup server that
  the backup user can't reach; a recycle bin isn't enough, since Synology's doesn't keep files deleted over rsync.
  The backup key is installed with `restrict,from=...`, and a Synology also needs its rsync and user home
  services on.

### Security

- Every service drops every Linux capability and runs with `no-new-privileges`; Nginx Proxy Manager and Uptime
  Kuma add back only the capabilities they need, from Docker's default set. Every service except Nginx Proxy
  Manager has a read-only root filesystem. The table is in docs/security.md#hardening.
- The policy check enforces it: new rules `no-new-privileges` and `cap-drop`, and `cap-add` now fails only on a
  capability outside Docker's default set.
- The smoke test also checks that Uptime Kuma can still ping.

## [0.1.0] - 2026-10-07

The first release: the Ares stack as a Compose file, every image pinned by version tag and digest for
`linux/arm64`, with health checks, autoheal, backups and release signing around it.

### Upgrading

- Uptime Kuma's slim image has no Chromium: change any "Real Browser" monitor to another type before upgrading.
- PeaNUT 6 runs as uid 1000 (`chown 1000:1000` its settings directory), puts its web UI and API behind a login it
  asks for on first start, and its metrics then need that login (HTTP Basic auth works for Prometheus).
- Portainer updates are no longer merged automatically: the server and its agents are updated together.

### Added

- `compose.yaml` with 6 services: Nginx Proxy Manager 2.16.0, Uptime Kuma 2.5.5 (slim), PeaNUT 6.0.0 and
  Portainer CE 2.39.8 (Alpine variant), each pinned by version tag and digest for `linux/arm64`, plus autoheal and
  socket-proxy. Data paths, volumes and the proxy's network come from settings (`NPM_DATA_PATH`,
  `NPM_LETSENCRYPT_PATH`, `PROXY_NETWORK`, `UPTIME_KUMA_VOLUME`, `PEANUT_CONFIG_PATH`, `PORTAINER_VOLUME`), so an
  existing installation's data can be adopted; the proxy's network is created outside the stack, so its address
  range survives rebuilding it.
- A health check for every service, and autoheal, which restarts any service whose health check fails and can
  post each restart to a webhook (`WEBHOOK_URL` in the optional, gitignored `autoheal.env`). It reaches Docker only
  through `socket-proxy`, which allows listing, inspecting, restarting and stopping containers and nothing else,
  on an internal network with no published port. Labelled policy exceptions: `docker-socket` for Portainer and
  socket-proxy, `latest` for autoheal.
- The smoke test replaces `*_VOLUME` and `*_NETWORK` settings with throwaway ones, and checks that autoheal
  restarts a container that turns unhealthy.
- Project policies (`SECURITY.md`, `CONTRIBUTING.md`, `GOVERNANCE.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`) and
  docs: quick start, installing, upgrading, rebuilding, architecture, interfaces, security requirements,
  assurance case, dependencies, roadmap and verifying releases.
- `scripts/check_compose.py`: the stack's policy check (every image pinned as `name:tag@sha256:<digest>`, no
  `latest`, no build, nothing privileged, no added capabilities, host network or PID namespace, no Docker
  socket mount, a health check on every service, unless a service's `org.honeybeartech.ares.allow.<rule>`
  label gives the reason), and the CycloneDX SBOM of the images for releases; tests with a 90 % branch-coverage
  floor.
- `scripts/backup.sh` and `scripts/restore.sh`: back up every service's read-write data mounts and the
  settings files with a manifest and checksums (readable only by the user who ran it), and restore them after
  verifying the checksums and asking first. `scripts/smoke-test.sh` starts the stack with throwaway settings,
  waits until every service is healthy and runs a backup and restore round trip.
- CI on every change: ruff, yamllint, shellcheck, actionlint, gitleaks over the whole history, the checker's
  tests, the policy check and the smoke test on an arm64 runner. CodeQL,
  OpenSSF Scorecard, dependency review, a DCO check and a weekly image scan (Trivy) also run.
- Dependabot for the images, the Python tools and the Actions; patch and minor updates merge automatically
  once every required check passes, major updates wait for the maintainer.
- A release workflow that publishes a source archive, the SBOM, `SHA256SUMS` signed keylessly with cosign,
  and SLSA build provenance ([docs/verifying-releases.md](docs/verifying-releases.md)).

### Security

- Triage of the first image scan (2,525 HIGH and CRITICAL alerts with a fix upstream): Uptime Kuma moves to the
  slim image, without Chromium and the embedded MariaDB (1,890 → 146 alerts); Nginx Proxy Manager 2.16.0 (503 → 92);
  PeaNUT 6.0.0 (87 → 26, three critical issues in its web framework fixed); Portainer 2.39.8 (60 → 8). What's left,
  and why: [docs/dependencies.md](docs/dependencies.md#current-findings).

[Unreleased]: https://github.com/HoneyBearTech/homelab-ares/compare/v0.2.5...HEAD
[0.2.5]: https://github.com/HoneyBearTech/homelab-ares/releases/tag/v0.2.5
[0.2.4]: https://github.com/HoneyBearTech/homelab-ares/releases/tag/v0.2.4
[0.2.3]: https://github.com/HoneyBearTech/homelab-ares/releases/tag/v0.2.3
[0.2.2]: https://github.com/HoneyBearTech/homelab-ares/releases/tag/v0.2.2
[0.2.1]: https://github.com/HoneyBearTech/homelab-ares/releases/tag/v0.2.1
[0.2.0]: https://github.com/HoneyBearTech/homelab-ares/releases/tag/v0.2.0
[0.1.0]: https://github.com/HoneyBearTech/homelab-ares/releases/tag/v0.1.0
