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
| Images of the GitLab copy's pipeline (Python, Docker CLI, git, gitleaks, actionlint) | [`.gitlab-ci.yml`](../.gitlab-ci.yml) | version tag and digest | GitLab Runner (Docker executor) |

Each release carries a CycloneDX SBOM listing every service's image and digest
([verifying-releases.md](verifying-releases.md)). To update the pinned Python tools, edit
`requirements-dev.in` if needed and run `pip-compile --generate-hashes --strip-extras requirements-dev.in`.

## Tracking dependencies

- **Renovate** ([`renovate.json`](../renovate.json)) runs before 06:00 each Monday in `America/Chicago` and
  proposes updates for the root Compose file, pip requirements, and GitHub Actions, covering all three entries
  formerly configured in Dependabot. Minor and patch updates are grouped; major updates use a separate group
  with a `major` label. The dependency dashboard tracks pending work. CI and required review apply to every PR.
- **No automatic merging**: `automerge` is explicitly false. The maintainer reviews and merges every update,
  including image rebuilds, Portainer changes, and majors. A new major can migrate service data one way, so the
  maintainer takes a backup before merging; a revert alone doesn't undo that migration.
- Renovate's `vulnerabilityAlerts` option is its vulnerability-alert PR path. Renovate's experimental
  `osvVulnerabilityAlerts` feature covers direct dependencies only for the `crate`, `go`, `hackage`, and `hex`
  data sources; it does **not** provide OSV coverage for this repository's Compose, pip, or GitHub Actions
  managers. Existing GitHub Dependabot alerts and security settings are separate, unchanged repository settings.
- **A merge deploys.** The maintainer's server follows `main` with a pull agent, so every merge reaches it within
  about two minutes ([upgrading.md](upgrading.md#following-main)). The maintainer takes a backup before merging.
- **Dependency review** ([`.github/workflows/dependency-review.yml`](../.github/workflows/dependency-review.yml))
  blocks a pull request that adds or changes a Python or Actions dependency with a known vulnerability of
  moderate severity or higher, or a license outside the allowlist.
- The CI-only images in `run:` steps, the images in `.gitlab-ci.yml` and the scripts' busybox image aren't in
  Renovate's configured managers; they're bumped by hand at least every quarter.
- **Nothing on the host updates from a registry.** Auto-updaters such as Watchtower are not used: they would run
  versions nobody reviewed. The pull agent only applies commits merged into `main`.

## Policy for vulnerabilities in dependencies

Known vulnerabilities are found through GitHub Dependabot alerts, Renovate vulnerability-alert PRs, the services'
and images' own advisories, and a
weekly scan of the pinned digests ([`scan.yml`](../.github/workflows/scan.yml): Trivy, HIGH and CRITICAL
findings that have a fix, for `linux/arm64`, reported to code scanning with one category per image). Each
finding is triaged within 14 days:

1. **If a fixed version exists**, bump to it (a Renovate pull request usually already does; the merge deploys
   it to the maintainer's server) and release it for those who run releases. A fix for an exploitable critical or
   high-severity vulnerability goes out in a patch release within 30 days; others go out with the next release.
2. **If upstream hasn't released a fix**, assess whether it's reachable in this stack (which ports are
   published, and above all whether it's reachable through the proxy from the internet). If it is, mitigate it
   where possible (for example, an access list or not publishing a port) and say so in the release notes;
   otherwise record the reason when dismissing the alert. Either way, it's fixed by a bump when upstream ships
   one.
3. **If an image is abandoned** and keeps accumulating vulnerabilities, replace it.

### Current findings

Triaged 4 November 2026, from the alerts open in code scanning after the weekly scan of 2 November and a scan of
each pinned digest that day with the same Trivy version and options. Where the answer depended on what an image
contains or how a library is used, the pinned image was inspected. Since 22 October, alerts are left open rather than
dismissed, so they close by themselves when an update ships the fix and a finding that becomes reachable isn't
hidden; the 100 dismissed on 7 October ([below](#first-triage-7-october-2026)) stay dismissed.

**172 open alerts: 9 critical, 160 high, 3 medium** (239 on 22 October). 185 closed since: 98 (6 critical) with
Uptime Kuma 2.5.7, built on a rebuilt base image; 25 with PeaNUT 6.1.0 and 5 with Portainer 2.45.3; and 57 of Nginx
Proxy Manager's kernel header alerts without a new image, as Trivy's database was revised. 58 of the open alerts are
new since 22 October, 29 of them in those kernel headers.

| Image | Open (critical) | Fixed by a bump? | Action |
| --- | --- | --- | --- |
| Nginx Proxy Manager `2.16.0` | 104 (5) | No: the newest release (24 September), not rebuilt since | Wait for upstream; keep the admin port on the LAN (below) |
| Uptime Kuma `2.5.7-slim` (scan snapshot) | 60 (2) | Partly: 2.5.9 (31 October) fixes 5 (`undici`, `follow-redirects`) and two advisories of its own (below) | This migration updates to 2.5.9; rescan after merge to verify the remaining findings |
| Portainer `2.45.3-alpine` | 5 (0) | No: the newest long-term-support release | Wait for upstream |
| PeaNUT `6.1.1` | 3 (2) | No: 6.1.2 (28 October) still ships Next.js 16.3.8 | Wait for upstream |
| autoheal, socket-proxy | 0 | | |

The next weekly scan (9 November) will also report what Trivy's database learnt after 2 November: 51 more high and
1 critical (CVE-2026-99083) in Nginx Proxy Manager's kernel headers and a high one in Uptime Kuma's `body-parser`,
while 2 kernel header alerts close: about 223 open, 10 critical, before Uptime Kuma 2.5.9.

**The critical findings, and the notable new high ones:**

| Image | Component | Advisory | Fixed in | Reachable? | Action |
| --- | --- | --- | --- | --- | --- |
| Nginx Proxy Manager | Brotli: `libbrotli1` 1.1.0-2+b7, and the copy built into Node.js 22.23.2 | **Critical**, new: CVE-2026-111497 (a crafted Brotli stream corrupts the decoder's memory) | `libbrotli1` 1.1.0-2+deb13u1; Node.js 22.23.4 (21 October) | **Yes, through Node.js, on the admin port and before login.** The Debian package isn't reachable: only `curl` links it, and `curl` runs only the health check. But the admin API decodes Brotli-compressed request bodies (`body-parser` 2.3.0) with the Brotli built into its Node.js, which the scan doesn't see | Wait for upstream (a release on Node.js 22.23.4 or later); keep port 81 on the LAN, as the [installation guide](installing.md#running-it-securely) says |
| Nginx Proxy Manager | body-parser 2.3.0 | High, new: CVE-2026-111181 | 2.4.0 | Yes, on the admin port and before login: one request crashes the admin API. Its supervisor restarts it, and the proxy keeps serving | Wait for upstream |
| Nginx Proxy Manager | proxy-addr 2.0.7 | **Critical**: CVE-2026-90711 | 2.0.8 | No, as on 22 October: Express' `trust proxy` is `true`, so no subnet is matched, and the API is on the admin port | Wait for upstream |
| Nginx Proxy Manager | certifi 2026.7.22 (certbot's) and 2026.6.17 (inside pip) | **Critical**: GHSA-6q48-6c7w-9gw2 | 2026.10.18 | Hard to reach, as on 22 October: it takes one of the compromised eMudhra intermediate keys *and* a position on the path of certbot's HTTPS connections. pip never runs | Wait for upstream |
| Nginx Proxy Manager | linux-libc-dev 6.12.107-1 | **Critical**: CVE-2026-98432 (and 53 high); from the next scan CVE-2026-99083 too | 6.12.113-1, 6.12.115-2 | No: kernel header files for compiling; nothing in the image executes them, and containers run on the host's kernel | Wait for upstream |
| Nginx Proxy Manager | undici 8.10.2 and 6.28.0 | 8 high, new | 8.12.2 | No. The admin API's copy is there for its schema loader to fetch remote references, and its schema refers only to its own files; node-gyp's copy is only for building | Wait for upstream |
| Nginx Proxy Manager | filelock 4.0.1 (certbot's), msgpack 1.1.2 (inside pip) | 3 high | 4.2.1, 1.2.3 | No: the `filelock` flaw needs a local user who can rename files in certbot's directories; pip never runs | Wait for upstream |
| Uptime Kuma | Brotli: `libbrotli1` 1.0.9-2+b6 | **Critical**, new: CVE-2026-111497 | 1.0.9-2+deb12u1 | No. Only `curl` links it, and nothing in Uptime Kuma runs `curl` (its health check is a Go binary). Its Node.js, 22.23.4, has the fix for its own Brotli | Wait for upstream (still in 2.5.9) |
| Uptime Kuma | protobufjs 7.2.6 | **Critical**: CVE-2026-41242 (and 5 high) | 7.5.5 | Only with Uptime Kuma's login, as on 22 October: it compiles a protobuf definition only for a gRPC monitor, from the text its user typed into that monitor | Wait for upstream (still in 2.5.9) |
| Uptime Kuma | undici 6.28.1 (cheerio's), follow-redirects 1.16.0, @azure/msal-node 5.6.0 | 6 high and a medium, new | 6.29.1, 1.16.2, 7.1.0 | Only through monitors its user configures behind its login; `msal-node`'s flaw is in an interactive sign-in flow that a monitor doesn't use | Bump to 2.5.9, which fixes `undici`'s and two of `follow-redirects`' |
| Uptime Kuma | OpenSSL 3.0.22-1~deb12u1 | 2 high, new | 3.0.22-1~deb12u2 | No: the flaw is in DTLS, and Node.js uses its own OpenSSL | Wait for upstream |
| Uptime Kuma | `cloudflared` 2026.10.3 (`go-jose`, `klauspost/compress`); Go standard library in the health check | 6 high | | No: `cloudflared` runs only with a Cloudflare Tunnel token set in Uptime Kuma; the health check only sends one HTTP request inside the container, like the 27 alerts dismissed for it on 7 October | Wait for upstream |
| PeaNUT 6.1.1 | Next.js 16.3.8 | **Critical**, new: GHSA-673q-mjm6-r5xr, GHSA-2464-fhr4-w9xw (and CVE-2026-94482, high) | 16.4.1 | Not the critical ones. The first is in image optimization through `sharp`: PeaNUT turns image optimization off, doesn't allow SVG, and ships `sharp` 0.35.5, the advisory's workaround. The second needs a `use cache` function, and PeaNUT doesn't enable `use cache`. The high one (one request can tie up the server through a Server Action) is reachable on PeaNUT's port on the LAN | Wait for upstream |
| Portainer | containerd, BuildKit, `go-archive`, `docker/cli` (Go modules) | 5 high | | No, as on 22 October: all of Portainer is behind its login, and containerd's flaw is in restoring a checkpoint, which the host's runtime does | Waits for the maintainer |

**Uptime Kuma's own advisories**, which the image scan doesn't report: GHSA-v2p3-6f5h-6hhf (high, fixed in 2.5.8),
command-line injection through the Apprise notification settings, needs Uptime Kuma's login; GHSA-86ch-2247-gr56
(medium, fixed in 2.5.9) lets anyone who can reach a status page's RSS feed poison its cached link for 5 minutes. Both
arrive with 2.5.9. 2.5.8 also drops TLS from the TCP Port monitor: such monitors become plain TCP checks.

**The rest** wait for upstream, as on 22 October: Uptime Kuma's other Node modules (`tar`, `nodemailer`, `liquidjs`,
`@grpc/grpc-js`, `axios`, `minimatch`, …), reached only through monitors, notifications and templates that its user
configures behind its login (`ws` 8.19.0 is only the WebSocket monitor's client); Nginx Proxy Manager's Debian
packages (`apache2-utils` without Apache httpd, Expat, which nginx doesn't use, `curl` for the health check, OpenSSL,
PCRE2) and its Node modules (`brace-expansion`, `basic-ftp`); the npm command line's own modules in Uptime Kuma, which
never run; certbot's `cryptography`; and the packages pip carries inside itself (`urllib3`, `setuptools`), which never
run either.

**Watch: Uptime Kuma's slim base image.** Uptime Kuma's `base2-slim` image was rebuilt on 23 October (Debian 12.15),
for the first time since 31 May, and 2.5.7-slim is built on it: that closed the Perl and GnuTLS findings and
`cloudflared`'s gRPC-Go one. Its one Debian critical now (`libbrotli1`) has a Debian update from after that rebuild.
The full image isn't a way out while it bundles Chromium ([below](#first-triage-7-october-2026)). The watch is
re-checked monthly; if the slim base falls months behind Debian's updates again by the January 2027 quarterly review,
the maintainer decides there between asking upstream for a rebuild and step 3.

**autoheal** (`journeyover/docker-autoheal`): pinned to the maintained 2.0.2 version and verified multi-platform
index digest in `compose.yaml`; its process command supports the existing `pgrep -f autoheal` health check.

### First triage (7 October 2026)

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

## Licenses

homelab-ares's own files are MIT-licensed. The Python tools must be under an OSI-approved license that
dependency review allows (MIT, Apache-2.0, BSD, ISC, PSF, MPL-2.0 and similar); yamllint (GPL-3.0) is
allowed as a development tool. The images keep their own licenses.

## Policy for findings from static analysis (SAST)

CodeQL analyses the checker and the workflows on every pull request and weekly, and ruff runs the bandit
security rules in CI. A CodeQL finding of medium severity or higher is fixed before the next release, or,
if it is a false positive, dismissed in code scanning with a written reason. A ruff or shellcheck finding fails
CI; a deliberate exception is a per-line `noqa` or `shellcheck disable` with the reason next to it.
