# Roadmap

Where homelab-ares is going over roughly the next twelve months (from October 2026). Plans change; this
file changes with them, in the same pull request.

## Now: the stack in git

- Done: the checks, backup and restore scripts, smoke test, release signing and documentation around the stack.
- Done: `compose.yaml` with Nginx Proxy Manager, Uptime Kuma, PeaNUT and Portainer, every image pinned by tag and
  digest for `linux/arm64`, a health check for each service, autoheal behind a filtering socket proxy, and the
  smoke test proving health, backup and restore, and autoheal's restarts on arm64 in CI.
- Done: first release (0.1.0) before Ares switches over, so the server is first deployed from a signed, verified
  version.
- Done: Ares runs the stack from a checkout of this repository, adopting the existing data, ports and networks
  so nothing that reaches the server noticed.
- Done: Ares follows `main` with a pull agent, so a merge deploys within minutes
  ([upgrading.md](upgrading.md#following-main)); backups and restores share the agent's lock so they never run
  during a deploy.

## Next: safe upgrades and rebuilds

- Done: the documented rebuild ([rebuilding.md](rebuilding.md)) rehearsed on a scratch machine from a real
  backup.
- Done: scheduled backups copied off the host (`scripts/scheduled-backup.sh`, a systemd timer), reported to Uptime
  Kuma.

## Later

- Non-root users for the services whose images allow it.
- Optional services as Compose profiles, so a smaller installation can leave them out.

## Security and project health

- Keep CI, CodeQL, Scorecard, dependency review and the DCO check green on every change.
- Branch protection on `main` with required checks; private vulnerability reporting; secret scanning with
  push protection.
- Keep the OpenSSF Best Practices **Passing** and **Silver** badges (both reached) and **OSPS Baseline** Levels 1
  and 2 (met).
- Signed releases with checksums, SBOM and SLSA provenance (every release since 0.1.0).

## What homelab-ares will not do

- **Build or patch images.** It runs upstream images unchanged; bugs in the services go to their projects.
- **Configure the services' internals** (proxy hosts, certificates, monitors, Portainer environments). Those are
  configured in each service and live in its data, which the backups cover.
- **Store secrets.** No logins, tokens or private keys in the repository, encrypted or not.
- **Auto-update from registries.** Every version change is a commit in `main` that passed CI; the server applies
  only those.
- **Run the monitoring stack** (Grafana, Prometheus, Loki). It has its own project, even where it shares the host.
- **Be a general-purpose homelab distribution.** It describes one server; others are welcome to fork or borrow
  from it, but options that only another setup needs are out of scope.
