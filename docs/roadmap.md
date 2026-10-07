# Roadmap

Where homelab-ares is going over roughly the next twelve months (from October 2026). Plans change; this
file changes with them, in the same pull request.

## Now: the stack in git

- Done: the checks, backup and restore scripts, smoke test, release signing and documentation around the stack.
- `compose.yaml` with Nginx Proxy Manager, Uptime Kuma, PeaNUT and Portainer, every image pinned by tag and
  digest for `linux/arm64`, a health check for each service, Dependabot proposing updates.
- The smoke test and the image scan running against the real stack in CI.
- First release (0.1.0) before Ares switches over, so the server is first deployed from a signed, verified
  version.
- Switch Ares to run the stack from a checkout of this repository, adopting the existing data, ports and
  networks so nothing that reaches the server notices.

## Next: safe upgrades and rebuilds

- Rehearse the documented rebuild ([rebuilding.md](rebuilding.md)) on a scratch machine.
- Scheduled backups copied off the host.

## Later

- Tighter container settings where the images allow it (read-only root filesystems, dropped capabilities,
  non-root users).
- Optional services as Compose profiles, so a smaller installation can leave them out.

## Security and project health

- Keep CI, CodeQL, Scorecard, dependency review and the DCO check green on every change.
- Branch protection on `main` with required checks; private vulnerability reporting; secret scanning with
  push protection.
- Reach the OpenSSF Best Practices **Passing** and **Silver** badges, and meet **OSPS Baseline** Levels 1
  and 2.
- Signed releases with checksums, SBOM and SLSA provenance from the first release on.

## What homelab-ares will not do

- **Build or patch images.** It runs upstream images unchanged; bugs in the services go to their projects.
- **Configure the services' internals** (proxy hosts, certificates, monitors, Portainer environments). Those are
  configured in each service and live in its data, which the backups cover.
- **Store secrets.** No logins, tokens or private keys in the repository, encrypted or not.
- **Auto-update.** Every version change is a reviewed commit.
- **Run the monitoring stack** (Grafana, Prometheus, Loki). It has its own project, even where it shares the host.
- **Be a general-purpose homelab distribution.** It describes one server; others are welcome to fork or borrow
  from it, but options that only another setup needs are out of scope.
