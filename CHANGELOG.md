# Changelog

All notable changes to homelab-ares are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `compose.yaml` with 6 services: Nginx Proxy Manager 2.15.1, Uptime Kuma 2.5.5, PeaNUT 5.10.0 and Portainer CE
  2.39.3 (Alpine variant), each pinned by version tag and digest for `linux/arm64`, plus autoheal and
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

[Unreleased]: https://github.com/HoneyBearTech/homelab-ares/commits/main
