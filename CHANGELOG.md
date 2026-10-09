# Changelog

All notable changes to homelab-ares are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/HoneyBearTech/homelab-ares/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/HoneyBearTech/homelab-ares/releases/tag/v0.1.0
