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

- **Dependabot** ([`.github/dependabot.yml`](../.github/dependabot.yml)) checks weekly for new image
  versions in the Compose file, new tool versions and new Action versions, and opens a pull request for
  each. Dependabot alerts and security updates are on.
- **Patch, minor and major updates merge automatically**
  ([`.github/workflows/dependabot-auto-merge.yml`](../.github/workflows/dependabot-auto-merge.yml)): for the
  images, the Python tools and the GitHub Actions, they're squash-merged once every required check has passed
  (CI with the Compose policy check and the smoke test, CodeQL, dependency review). Nothing skips a check, and
  a failing update stays open for the maintainer.
- **Image rebuilds merge automatically too**: a pull request that only moves an image to a new digest under the
  same tag (a rebuild of the same app version, with newer base packages) and changes nothing else in `compose.yaml`.
  Portainer's rebuilds wait, like its version updates.
- **Major updates merge automatically too** (the maintainer's decision, 2026-10-14), so they reach the
  maintainer's server unattended. A new major version can migrate a service's data one way: the nightly backup
  is the way back, since a revert alone doesn't undo the migration.
- **Merged by hand**: any update Dependabot can't classify as patch, minor or major, and every Portainer update
  (its server and the agents on the other hosts move together).
- **A merge deploys.** The maintainer's server follows `main` with a pull agent, so every merge, the automatic
  ones included, reaches it within about two minutes ([upgrading.md](upgrading.md#following-main)). So every
  automatic merge relies on the nightly [scheduled backup](installing.md#scheduled-backups), and the
  maintainer takes a backup before merging the updates that wait.
- **Dependency review** ([`.github/workflows/dependency-review.yml`](../.github/workflows/dependency-review.yml))
  blocks a pull request that adds or changes a Python or Actions dependency with a known vulnerability of
  moderate severity or higher, or a license outside the allowlist.
- The CI-only images in `run:` steps, the images in `.gitlab-ci.yml` and the scripts' busybox image aren't seen
  by Dependabot; they're bumped by hand at least every quarter.
- **Nothing on the host updates from a registry.** Auto-updaters such as Watchtower are not used: they would run
  versions nobody reviewed. The pull agent only applies commits merged into `main`.

## Policy for vulnerabilities in dependencies

Known vulnerabilities are found through Dependabot alerts, the services' and images' own advisories, and a
weekly scan of the pinned digests ([`scan.yml`](../.github/workflows/scan.yml): Trivy, HIGH and CRITICAL
findings that have a fix, for `linux/arm64`, reported to code scanning with one category per image). Each
finding is triaged within 14 days:

1. **If a fixed version exists**, bump to it (a Dependabot pull request usually already does; the merge deploys
   it to the maintainer's server) and release it for those who run releases. A fix for an exploitable critical or
   high-severity vulnerability goes out in a patch release within 30 days; others go out with the next release.
2. **If upstream hasn't released a fix**, assess whether it's reachable in this stack (which ports are
   published, and above all whether it's reachable through the proxy from the internet). If it is, mitigate it
   where possible (for example, an access list or not publishing a port) and say so in the release notes;
   otherwise record the reason when dismissing the alert. Either way, it's fixed by a bump when upstream ships
   one.
3. **If an image is abandoned** and keeps accumulating vulnerabilities, replace it.

### Current findings

Triaged 22 October 2026, from the alerts open in code scanning after the weekly scan of 19 October and a scan of
each pinned digest that day with the same Trivy version and options. Where the answer depended on what an image
contains or how a library is used, the pinned image was inspected. From this triage on, alerts are left open rather
than dismissed, so they close by themselves when an update ships the fix and a finding that becomes reachable isn't
hidden; the 100 dismissed on 7 October ([below](#first-triage-7-october-2026)) stay dismissed.

**239 open alerts: 11 critical, 225 high, 3 medium** (199 on 14 October). Of the 45 new ones, 43 are Debian
security updates newer than Nginx Proxy Manager's build (kernel headers, `apache2-utils`, curl, Expat), one is a Go
module in Portainer and one in the `cloudflared` binary that Uptime Kuma bundles; 5 closed with Uptime Kuma 2.5.6.

| Image | Open (critical) | Fixed by a bump? | Action |
| --- | --- | --- | --- |
| Uptime Kuma `2.5.6-slim` | 143 (7) | No: the newest release, and its tag hasn't been rebuilt | Wait for upstream; **watch** its base image (below) |
| Nginx Proxy Manager `2.16.0` | 62 (1) | No: the newest release (24 September), not rebuilt since | Wait for upstream |
| PeaNUT `6.0.0` | 25 (3) | **Yes**: 6.1.0, merged on 21 October (#43). A scan of its digest finds nothing: it ships Next.js 16.3.8, sharp 0.35.5 and Debian 13.7 | Done. The alerts close at the next weekly scan: a merge by Dependabot's auto-merge doesn't start the scan |
| Portainer `2.45.2-alpine` | 9 (0) | Partly: 2.45.3 (21 October) fixes 4 (Go standard library, `x/net`) | Updated to 2.45.3 on 22 October (the maintainer's decision); the other 5 wait for upstream |
| autoheal, socket-proxy | 0 | | |

The next weekly scan (26 October) will also report what Trivy's database learnt after 19 October: 52 more alerts in
Nginx Proxy Manager (50 in the kernel headers, 4 of them critical, and `certifi`, 2 critical), 6 high in Uptime
Kuma and 1 in Portainer, while PeaNUT's 25 close: about 273 open, 14 critical.

**The critical findings, and the notable new high ones:**

| Image | Component | Advisory | Fixed in | Reachable? | Action |
| --- | --- | --- | --- | --- | --- |
| PeaNUT 6.0.0 | Next.js 16.2.4 | **Critical**: GHSA-vcvr-r3jv-pc5j, GHSA-2xp9-vwfh-vxw4, CVE-2026-75604 (and 11 high, 1 medium) | 16.3.3, 16.3.6 | No longer: PeaNUT 6.1.0 ships Next.js 16.3.8 | Bump in #43, merged |
| Uptime Kuma | protobufjs 7.2.6 | **Critical**: CVE-2026-41242 (and 5 high) | 7.5.5 (the high ones 7.5.6, 7.6.1) | Only with Uptime Kuma's login. It compiles a protobuf definition only for a gRPC monitor, from the text its user typed into that monitor | Wait for upstream |
| Uptime Kuma | gRPC-Go 1.79.2 in `cloudflared` 2026.5.2 | **Critical**: CVE-2026-33186 | 1.79.3 | No. Uptime Kuma starts `cloudflared` only when a Cloudflare Tunnel token is set in its settings, and it then connects out to Cloudflare. The flaw lets a client slip past path-based authorization in a gRPC server, and the binary doesn't contain gRPC-Go's authorization package (`grpc/authz`). The same holds for `cloudflared`'s 31 other alerts (Go standard library, `x/crypto`, `x/net`, `x/text`) | Wait for upstream |
| Uptime Kuma | perl-base 5.36.0-7+deb12u3 | **Critical**: CVE-2026-8376, CVE-2026-13221, CVE-2026-42496 | 5.36.0-7+deb12u4 | No. Nothing in Uptime Kuma runs Perl; it's there as part of Debian's base system. CVE-2026-8376 affects 32-bit builds only (the arm64 image is 64-bit), and CVE-2026-42496 is in Archive::Tar, which isn't in the image | Wait for upstream (stale base) |
| Uptime Kuma | GnuTLS 3.7.9-2+deb12u6 | **Critical**: CVE-2026-42010, CVE-2026-33845 | 3.7.9-2+deb12u7 | No. The flaws are in a server's RSA-PSK login and in DTLS. Uptime Kuma (Node.js) uses its own OpenSSL; GnuTLS is linked only by apt's download methods and the LDAP and RTMP libraries behind `curl`, none of them a server or using DTLS | Wait for upstream (stale base) |
| Nginx Proxy Manager | proxy-addr 2.0.7 | **Critical**: CVE-2026-90711 | 2.0.8 | No. The flaw is in a trusted subnet written in IPv4-mapped IPv6 notation. Nginx Proxy Manager's API sets Express' `trust proxy` to `true` (checked in the image), so no subnet is matched, and the API is on the admin port | Wait for upstream |
| Nginx Proxy Manager | certifi 2026.7.22 (certbot's) and 2026.6.17 (inside pip) | **Critical**, from the next scan: GHSA-6q48-6c7w-9gw2 | 2026.10.19 | Hard to reach. certbot trusts certifi's bundle for its HTTPS connections (the ACME server, a DNS provider's API); exploiting it takes one of the compromised eMudhra intermediate keys *and* a position on the path of those connections. pip never runs | Wait for upstream (fixed upstream on 19 October) |
| Nginx Proxy Manager | linux-libc-dev 6.12.107-1 | 25 high (22 new); from the next scan 50 more, 4 **critical**: CVE-2026-90037, CVE-2026-98621, CVE-2026-98725, CVE-2026-98805 | 6.12.111-1, 6.12.113-1 | No: kernel header files for compiling; nothing in the image executes them, and containers run on the host's kernel | Wait for upstream |
| Nginx Proxy Manager | apache2-utils 2.4.68-1~deb13u1 | 7 high, new | 2.4.69-1~deb13u1 | No. All seven are in Apache httpd's modules (`mod_rewrite`, `mod_auth_digest`, `mod_proxy_uwsgi`, …), and the image has no httpd, only the utilities; Nginx Proxy Manager hashes access-list passwords with `openssl passwd` | Wait for upstream |
| Nginx Proxy Manager | curl, libcurl 8.14.1-2+deb13u5 | 9 high, new | 8.14.1-2+deb13u7 | No: `curl` runs only the health check, over plain HTTP to the service's own API inside the container | Wait for upstream |
| Nginx Proxy Manager | Expat 2.8.3-1~deb13u1 | 5 high, new | 2.9.0-1~deb13u1 | Unlikely: nginx doesn't use Expat; Python (certbot), the Apache utilities and git do, and certbot's exchange with the ACME server is JSON | Wait for upstream |
| Portainer | containerd 2.2.5 (Go module) | High, new: CVE-2026-95837 | 2.2.7 | No: the privilege escalation is in restoring a container checkpoint, which the host's container runtime does; Portainer carries containerd's module only as a client. All of Portainer is behind its login | Waits for the maintainer; still in 2.45.3 |

**The rest** wait for upstream, as on 7 October: Uptime Kuma's other Node modules (`tar`, `nodemailer`, `liquidjs`,
`@grpc/grpc-js`, `axios`, `minimatch`, …), reached only through monitors, notifications and templates that its user
configures behind its login (`ws` 8.19.0 is only the WebSocket monitor's client: Uptime Kuma's own socket server uses
`ws` 8.21.3, which has the fix), and its Debian 12 packages (Python, which only the Apprise notification provider
runs; Expat, PCRE2, curl, OpenSSL, libssh2); the npm command line's own modules in both images, which never run;
certbot's Python packages in Nginx Proxy Manager (`cryptography`, `urllib3`); and Portainer's other Go modules
(BuildKit, `go-archive`, and `docker/cli`, whose flaw affects Windows only), behind Portainer's login.

**Watch: Uptime Kuma's slim base image.** `2.5.6-slim`, built on 9 October, is Uptime Kuma's `base2-slim` image
(the same layers) plus the app, and that base was last rebuilt on 31 May 2026, so it lacks Debian 12's updates since
then: 5 of its 7 critical findings (Perl, GnuTLS) have fixed Debian packages, and the fixes for the other two
(protobufjs, gRPC-Go) were published in March and April. The full image isn't a way out while it bundles Chromium
([below](#first-triage-7-october-2026)). The watch is re-checked monthly; if the slim base still hasn't been rebuilt
at the January 2027 quarterly review, the maintainer decides there between asking upstream for a rebuild and step 3.

**autoheal** (`willfarrell/autoheal`): its only maintained tag is `latest` (its versioned tags stop at 1.2.0 from
2021), so it is pinned as `latest@sha256:…` with a policy exception; if Dependabot doesn't propose new digests for
it, it's bumped by hand with the other hand-pinned images.

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
