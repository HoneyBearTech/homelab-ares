# Assurance case

Why homelab-ares meets its [security requirements](security.md): the threat model, the trust boundaries,
the secure design principles it follows, and how common weaknesses are countered.

## Threat model

| Asset | Threat | Countered by |
| --- | --- | --- |
| The host | A compromised or malicious image | Digest pins; versions change only by reviewed pull request; no privileged, capability, host-namespace or socket access without a reasoned label |
| The host and every agent host | Portainer's login or Portainer itself compromised | Socket access limited to Portainer as a labelled exception; admin UI on the LAN only; strong unique password; updates through Dependabot |
| The proxied services | Traffic intercepted or a service exposed by mistake | TLS on the proxy; access lists for LAN-only services; admin ports kept off the internet ([installing.md](installing.md#running-it-securely)) |
| TLS private keys, logins, tokens | Committed to the public repository | Kept in the services' data, never in the repo; `.gitignore`; gitleaks over the history in CI; GitHub push protection |
| TLS private keys, logins, tokens | Leaked through a backup | `scripts/backup.sh` writes backups readable only by the user who ran it; documented as secret, to be kept off the host |
| The services' data | An upgrade that migrates and breaks it | `scripts/backup.sh` before every upgrade; rollback = old tag + `scripts/restore.sh`, both exercised by the CI smoke test |
| The host | A container breaking out through the Docker socket | The `docker-socket` rule; only Portainer and socket-proxy mount it, as labelled exceptions; autoheal reaches Docker only through socket-proxy, which allows listing, inspecting, restarting and stopping containers, on an internal network |
| Availability | A service hangs without exiting | A health check on every service; autoheal restarts an unhealthy one (and can notify a webhook); a long start period keeps it from interrupting a migration |
| The services' data | A crafted backup writing outside the services' data | `restore.sh` verifies `SHA256SUMS` (which covers the `MANIFEST`), accepts only plain archive names and absolute container paths without `..`, refuses the Docker socket, and writes only a mount the service has read-write |
| The release | Tampered release files | Keyless-signed `SHA256SUMS`, SLSA provenance, signed tags |
| The CI pipeline | Untrusted pull request input running with credentials | `pull_request` only, read-only token by default, untrusted values only via `env:`, actions pinned by SHA |
| Operator privacy | Hostnames, addresses, domains or paths in the public repo | Placeholders only; reviewed in every pull request |

Attackers considered: a compromised upstream image or registry tag; someone on the internet reaching the proxy;
someone on the LAN reaching an admin UI; a malicious pull request; a tampered backup. Out of scope: an attacker
who already has root or `docker` group access on the host, or write access to `.env` or the services' data.

## Trust boundaries

1. **Registries → host.** Images are trusted only at the digest a reviewed commit names.
2. **Repository → host.** The host runs a tagged, signed release or a reviewed `main`; it never pulls code
   that wasn't merged.
3. **Internet → proxy.** Only ports 80 and 443 are meant to be reachable from outside; everything behind them is
   configured per proxy host, with TLS and access lists.
4. **LAN → admin UIs.** Each admin UI is behind the service's own login and isn't published beyond the LAN.
5. **Containers → host.** Only each service's data directory or volume is mounted; no host namespaces. The two
   socket mounts (Portainer; socket-proxy, which autoheal reaches only on an internal network) are reviewed,
   labelled exceptions.
6. **Ares → other Docker hosts.** Portainer's agents obey only their paired server; that pairing makes this
   server's Portainer the key to every agent host.
7. **Pull requests → CI.** Fork pull requests get a read-only token and no secrets.

## Secure design principles

- **Least privilege**: every capability dropped and only the needed ones added back, no new privileges, no host
  namespaces, one documented socket mount, read-only CI tokens raised per job.
- **Fail-safe defaults**: the policy check fails on anything it doesn't recognise as allowed; an exception
  needs a reason, in the file, in review. `restore.sh` refuses anything in a backup it can't account for.
- **Complete mediation**: every change to what runs passes through a pull request and the same checks;
  nothing on the host updates itself.
- **Economy of mechanism**: one Compose file, one standard-library checker, upstream images unchanged.
- **Separation of privilege**: secrets live with the services, settings in `.env`, configuration in git.
- **Open design**: the whole configuration, policy and release process are public.

## Common weaknesses

| Weakness | Where it could arise | How it's countered |
| --- | --- | --- |
| CWE-494 (code downloaded without integrity check) | Image pulls | Digest pins; signed release checksums |
| CWE-798 / CWE-312 (hard-coded or cleartext credentials) | Compose `environment:`, `.env`, docs | No secrets in the repo; gitleaks; push protection |
| CWE-250 (unnecessary privileges) | Container settings | Policy rules `privileged`, `no-new-privileges`, `cap-drop`, `cap-add`, `host-*`, `docker-socket`; read-only root filesystems where the images allow it |
| CWE-1393 (default passwords) | Nginx Proxy Manager's first start | Documented as the first step of setup ([quick-start.md](quick-start.md)) |
| CWE-22 (path traversal) | Restoring a backup | `restore.sh` validates archive names and mount paths from the checksummed `MANIFEST` |
| CWE-1104 (unmaintained third-party components) | Images, tools, Actions | Dependabot weekly; image scan; triage SLAs ([dependencies.md](dependencies.md)) |
| CWE-77/78 (injection) | Workflows, scripts | Untrusted values only via `env:`; actionlint and shellcheck; CodeQL for Actions |
| CWE-20 (improper input validation) | The checker's input | It reads JSON only with the standard library, never evaluates it, and exits 2 on anything that isn't a JSON object |

## Evidence

- CI on every change: ruff (with the bandit rules), yamllint, actionlint, gitleaks over the history,
  shellcheck, pytest with a 90 % branch-coverage floor, `docker compose config`, the policy check, and a smoke
  test on arm64 that starts every pinned image, waits for its health check, round-trips a backup and restore and
  proves that autoheal restarts an unhealthy container (a dynamic test of the stack and the scripts).
- A weekly Trivy scan of every pinned image, and on every change to `compose.yaml`, into code scanning.
- CodeQL (Python and Actions) on every pull request and weekly; OpenSSF Scorecard weekly; dependency
  review on every pull request.
