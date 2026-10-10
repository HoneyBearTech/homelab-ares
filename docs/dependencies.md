# Dependencies and vulnerability management

How homelab-ares chooses, obtains, tracks and updates what it's built from, and what happens when one of
those dependencies has a vulnerability.

homelab-ares's dependencies are almost entirely the **container images** it runs. The rest are the tools its checks and tests use and the GitHub Actions in its workflows. Its
own code, the policy checker, uses only the Python standard library.

## Choosing a dependency

A new image or tool must:

- be open source under an OSI-approved license (the services' own licenses apply to them: homelab-ares pins and
  runs them, it doesn't redistribute or link them);
- be actively maintained: releases in the last year, security issues answered, and **published for
  `linux/arm64`**, the host's architecture;
- come from the project itself, from its official registry; and
- be worth it: a new service needs a reason in the pull request that adds it.

## Obtaining dependencies

| Dependency | Declared in | Pinned by | Fetched by |
| --- | --- | --- | --- |
| The stack's images | [`compose.yaml`](../compose.yaml) | version tag and digest | `docker compose pull` |
| Check and test tools (pytest, coverage, ruff, yamllint, shellcheck) | [`requirements-dev.in`](../requirements-dev.in) → [`requirements-dev.txt`](../requirements-dev.txt) | exact version and SHA-256 hashes (`pip-compile --generate-hashes`) | `pip install --require-hashes --no-deps` |
| Helper image for backups and the smoke test (busybox) | [`scripts/lib.sh`](../scripts/lib.sh) | version tag and digest | Docker |
| Linters and scanners used only by CI (actionlint, gitleaks, Trivy) | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml), [`scan.yml`](../.github/workflows/scan.yml) | version tag and digest | Docker |
| GitHub Actions | [`.github/workflows/`](../.github/workflows/) | full commit SHA (version in a comment) | GitHub Actions |

Each release carries a CycloneDX SBOM listing every service's image and digest
([verifying-releases.md](verifying-releases.md)). To update the pinned Python tools, edit
`requirements-dev.in` if needed and run `pip-compile --generate-hashes --strip-extras requirements-dev.in`.

## Tracking dependencies

- **Dependabot** ([`.github/dependabot.yml`](../.github/dependabot.yml)) checks weekly for new image
  versions in the Compose file, new tool versions and new Action versions, and opens a pull request for
  each. Dependabot alerts and security updates are on.
- **Patch and minor updates merge automatically**
  ([`.github/workflows/dependabot-auto-merge.yml`](../.github/workflows/dependabot-auto-merge.yml)): for the
  images, the Python tools and the GitHub Actions, they're squash-merged once every required check has passed
  (CI with the Compose policy check and the smoke test, CodeQL, dependency review). Nothing skips a check, and
  a failing update stays open for the maintainer.
- **Major updates are merged by hand**, after reading the service's release notes: a new major version can
  migrate its data one way. So is any update Dependabot can't classify as patch, minor or major, and every
  Portainer update: its server and the agents on the other hosts move together.
- **A merge doesn't deploy.** The server runs what it last pulled; updates reach it when the operator pulls
  and redeploys, with a backup first ([upgrading.md](upgrading.md)).
- **Dependency review** ([`.github/workflows/dependency-review.yml`](../.github/workflows/dependency-review.yml))
  blocks a pull request that adds or changes a Python or Actions dependency with a known vulnerability of
  moderate severity or higher, or a license outside the allowlist.
- The CI-only images in `run:` steps and the scripts' busybox image aren't seen by Dependabot; they're bumped
  by hand at least every quarter.
- **Nothing updates itself on the host.** Auto-updaters such as Watchtower are not used: they would run
  versions nobody reviewed.

## Policy for vulnerabilities in dependencies

Known vulnerabilities are found through Dependabot alerts, the services' and images' own advisories, and a
weekly scan of the pinned digests ([`scan.yml`](../.github/workflows/scan.yml): Trivy, HIGH and CRITICAL
findings that have a fix, for `linux/arm64`, reported to code scanning with one category per image). Each
finding is triaged within 14 days:

1. **If a fixed version exists**, bump to it (a Dependabot pull request usually already does) and release.
   A fix for an exploitable critical or high-severity vulnerability goes out in a patch release within 30
   days; others go out with the next release.
2. **If upstream hasn't released a fix**, assess whether it's reachable in this stack (which ports are
   published, and above all whether it's reachable through the proxy from the internet). If it is, mitigate it
   where possible (for example, an access list or not publishing a port) and say so in the release notes;
   otherwise record the reason when dismissing the alert. Either way, it's fixed by a bump when upstream ships
   one.
3. **If an image is abandoned** and keeps accumulating vulnerabilities, replace it.

### Current findings

Triaged 7 October 2026, after the first image scan: 2,525 alerts, every one HIGH or CRITICAL with a fixed package
version somewhere upstream (Uptime Kuma 1,880, Nginx Proxy Manager 503, PeaNUT 75, Portainer 60, autoheal and
socket-proxy none).

**Fixed by a bump or a leaner image** (counts from the same scan of each image, `linux/arm64`):

| Image | Before | After | Change |
| --- | --- | --- | --- |
| Uptime Kuma | 2.5.5: 1,890 | 2.5.5-slim: 146 | The full image bundles Chromium (1,670 alerts by itself) for "Real Browser" monitors and an embedded MariaDB; this installation uses neither (its database is SQLite) |
| Nginx Proxy Manager | 2.15.1: 503 | 2.16.0: 92 | Rebuilt on newer Debian packages and Node modules |
| PeaNUT | 5.10.0: 87 | 6.0.0: 26 | Fixes three critical issues in its web framework (Next.js); 6.0 also puts its web UI and API behind a login ([interfaces.md](interfaces.md#settings)) |
| Portainer | 2.39.3: 60 | 2.39.8: 8 | A patch release on the same long-term-support line, so the agents on other hosts stay compatible |

After these changes the scan on `main` reported 269 open alerts. **Not reachable in this stack** (100 alerts,
dismissed in code scanning with this reason):

| Image | Package | Why it can't be reached |
| --- | --- | --- |
| Nginx Proxy Manager | `linux-libc-dev` | Kernel header files for compiling; nothing in the image executes them, and containers run on the host's kernel |
| Nginx Proxy Manager | the npm CLI's own modules under `/usr/lib/node_modules` (`brace-expansion`, `pacote`, `sigstore`, …) | The npm command line is only used to build the image; it never runs in the container |
| Uptime Kuma | Go standard library in `extra/healthcheck` | The health-check binary only sends one HTTP request to Uptime Kuma inside the container |

**Open, waiting for upstream** (169: Uptime Kuma 116, PeaNUT 26, Nginx Proxy Manager 19, Portainer 8). No newer
image exists yet with the fixed package; each alert closes by itself when a bump to such an image is merged and the
scan runs again. They're re-checked monthly.

- **OpenSSL** in Nginx Proxy Manager, PeaNUT and Portainer (Debian/Alpine security updates newer than the images'
  builds). Reachable through each service's TLS or HTTP endpoints; the admin UIs stay on the LAN.
- **Node.js modules** in Nginx Proxy Manager's admin API (among them `proxy-addr`, one critical) and PeaNUT's web UI
  (Next.js 16.2.4, two critical). Reachable only through the admin port 81 and PeaNUT's port 8080, which stay on the
  LAN; PeaNUT's are behind its login.
- **Uptime Kuma's remaining Debian packages** (Perl, GnuTLS, Expat, Python) and `cloudflared` (used only for a
  Cloudflare Tunnel, if one is configured in Uptime Kuma).
- **Portainer's Go modules** (`buildkit`, `docker/cli`, `grpc`): Portainer's UI and API stay on the LAN behind its
  login. Portainer is updated by hand together with its agents ([upgrading.md](upgrading.md#portainer-and-its-agents));
  it moved to the 2.45 long-term-support line in 0.2.4.

**autoheal** (`willfarrell/autoheal`): its only maintained tag is `latest` (its versioned tags stop at 1.2.0 from
2021), so it is pinned as `latest@sha256:…` with a policy exception; if Dependabot doesn't propose new digests for
it, it's bumped by hand with the other hand-pinned images.

## Licenses

homelab-ares's own files are MIT-licensed. The Python tools must be under an OSI-approved license that
dependency review allows (MIT, Apache-2.0, BSD, ISC, PSF, MPL-2.0 and similar); yamllint (GPL-3.0) is
allowed as a development tool. The images keep their own licenses.

## Policy for findings from static analysis (SAST)

CodeQL analyses the checker and the workflows on every pull request and weekly, and ruff runs the bandit
security rules in CI. A CodeQL finding of medium severity or higher is fixed before the next release, or,
if it is a false positive, dismissed in code scanning with a written reason. A ruff or shellcheck finding fails
CI; a deliberate exception is a per-line `noqa` or `shellcheck disable` with the reason next to it.
