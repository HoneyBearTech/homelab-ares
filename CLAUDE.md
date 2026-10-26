# homelab-ares

The Docker Compose stack for Ares, the owner's homelab edge and monitoring server (Debian 13, arm64, bare metal):
Nginx Proxy Manager, Uptime Kuma, PeaNUT and Portainer, plus autoheal behind a filtering socket proxy, every image
pinned by tag and digest so the server can be upgraded and rebuilt from this repository. Ares runs the stack from a
checkout of `main` that a pull agent deploys (see Deploys below); its nightly backups go off the host. This repo is
also the template for the other homelab stacks (homelab-atlas, -deimos, -helios, -hyperion): tooling that isn't
specific to Ares' services (checker, backup scripts, smoke test, workflows) is kept the same across them, so a change
here that isn't about Ares' own services is ported to them too, and vice versa.

## Before Making Structural Changes
Read the project's notes first. They live outside this repo, in the owner's Obsidian vault **Chronos** at
`~/Chronos/Projects/homelab-ares/` (every file is prefixed `homelab-ares-`):
- `homelab-ares-roadmap.md`: phases with checkboxes, including the OpenSSF phase and the owner's manual
  GitHub steps
- `homelab-ares-Pass-Map.md`: pass-by-pass delivery log; add a row when a pass ships
- `homelab-ares-Architecture.md`: the host, which containers run there today and which belong in this repo,
  data flow, deployment shape, cutover plan
- `homelab-ares-Security-Considerations.md`: assets, threats, trust boundaries, checklist (Ares terminates TLS
  for every proxied service and runs the Portainer server that controls every agent host: treat these notes as
  load-bearing)
- `homelab-ares-Decisions-Log.md`: ADR-style log (entries marked **Proposed** still need the owner's call)

Keep them current as work lands: tick roadmap checkboxes, add a Pass-Map row per pass, add dated
Decisions-Log entries. **The notes never go into this repo.** Chronos is versioned in its own private repo;
only commit or push it when the owner asks. The old in-repo vault path `.obsidian-docs/` stays gitignored.

## This repo is public
- No hostnames, IP addresses, internal or public domains, host paths, Portainer stack names or personal email
  addresses in anything committed: code, compose, docs, examples, tests, commit messages. Host facts live
  only in the Chronos notes. Examples use placeholders (`/srv/config`, `example.com`, `homelab-ares_`).
- Commit as `31805425+HoneyBearTech@users.noreply.github.com` (set as this repo's `user.email`), with
  `git commit -s` for the DCO sign-off; commits and tags are SSH-signed.
- No secrets: the services' logins, API tokens, TLS certificates and keys, and the NUT credentials stay in their
  data on the host, never in `compose.yaml`, `.env` or the `*.example` files. A secret a service can only take
  from its environment gets its own gitignored `<service>.env` (`env_file`) with a committed
  `<service>.env.example`. `.gitignore` covers `.env`, keys, certificates, `config/`, `appdata/`, `data/`, `backups/`;
  extend it rather than work around it. gitleaks runs over the whole history in CI.
- Keep the repo on track for OpenSSF Baseline Levels 1 and 2 and the Best Practices Passing and Silver
  badges. If a change would break a met criterion (for example unpinning an image or an Action, adding a
  workflow without `permissions:`, or dropping the coverage floor), say so before making it.

## Rules for the stack
- **Every image is pinned as `name:tag@sha256:<digest>`.** Never `latest`, never tag-only. Dependabot
  (`docker-compose` ecosystem) updates tag and digest together. Patch, minor and major updates (majors since
  owner 2026-10-14), and image rebuilds (same tag, new digest; owner 2026-10-14), are auto-merged once the required
  checks pass (`dependabot-auto-merge.yml`); every Portainer update waits for the owner (server and agents move
  together; owner's decision 2026-10-07), and so does any update Dependabot can't classify. Every merge deploys,
  the automatic ones included (see Deploys): a major reaches Ares unattended, with the nightly backup and a revert
  PR as the way back (restore from the backup if it migrated data one way).
- **Arm64.** Ares is arm64: every image must publish `linux/arm64`. The smoke test runs on an arm64 runner and
  the image scan scans `linux/arm64`.
- **No privileged containers, added capabilities, host network/PID, Docker socket mounts or device mappings** unless the
  service carries `org.honeybeartech.ares.allow.<rule>: "<reason>"` and the owner agreed.
  `scripts/check_compose.py` enforces both rules in CI and in the release workflow. Exceptions in use (each agreed
  by the owner, 2026-10-07): `portainer` (`docker-socket`, read-write: Portainer manages Docker on this host),
  `socket-proxy` (`docker-socket`, read-only: filters the API down to list/inspect/restart/stop for autoheal,
  internal network, no port), `autoheal` (`latest`: the image's only maintained tag). Don't add more without the
  owner agreeing.
- **Every service has a health check and the `autoheal: "true"` label** (except autoheal itself). autoheal must
  never get the socket itself, only `tcp://socket-proxy:2375`.
- **Never change the live server** (Ares) without the owner asking: merges only as **Merging** says, no
  `docker compose up`, no edits to service data, Portainer stacks or Nginx Proxy Manager's proxy hosts. Ares fronts
  every other service in the homelab, so a mistake there takes everything down. Read-only inspection (`docker ps`,
  `docker inspect`) only when asked.
- Every setting goes through `.env` (`${VAR:?…}` in compose when required) and is listed in `.env.example`
  and `docs/interfaces.md` (`tests/test_settings.py` checks both).
- **Data layout (owner's decision 2026-10-15, the same in every homelab stack)**: one required setting,
  `CONFIG_ROOT`; each service's settings and database live in `${CONFIG_ROOT}/<service>/config` (lowercase service
  name) mounted at the service's usual data path, and any other folder of its own beside it as
  `${CONFIG_ROOT}/<service>/<purpose>` (npm's `letsencrypt`, `logrotate`). No named Docker volumes for service data,
  and no per-service path or volume settings; `tests/test_settings.py` enforces it.
- **Never point a path setting into `/var/lib/docker/volumes`, and never keep service data in a named volume.**
  `docker volume prune`, `docker system prune --volumes` and Portainer's "remove unused volumes" delete every volume
  no container mounts *as a volume*, including one whose `_data` folder a service bind-mounts by path (that is how
  helios lost Plex's and Tautulli's data in 2026-10). Keep data under `CONFIG_ROOT`; the warning is in
  `docs/installing.md#where-data-lives`.
- **Container paths and network identity are load-bearing**: the services store paths in their databases,
  and other systems reach Ares by its published ports and Nginx Proxy Manager's network. Keep container paths,
  ports and networks the same when the host side moves; see the cutover plan in Chronos.
- `scripts/backup.sh` archives every read-write volume or bind mount except the Docker socket, anonymous volumes
  and the mounts a service's `org.honeybeartech.ares.backup.skip` label lists; paths inside a mount that its
  `org.honeybeartech.ares.backup.exclude` label lists (npm's `/data/logs`) are left out of the archive. Each
  service is stopped only while its data is copied; compression (pigz or gzip) runs after it starts again.
  `restore.sh` only writes mounts listed in the backup's MANIFEST that the service still mounts read-write, never
  a skipped mount, and leaves excluded paths and nested mounts in place; a service that bind-mounts a folder inside a
  mount it restores is stopped and started again with it. It writes to what compose.yaml mounts at
  that container path now (recreating a container made from an older compose.yaml, creating a missing directory), so
  a backup of an old volume restores into its `CONFIG_ROOT` folder. Keep it that way when adding a service.

## Deploys (owner's decision 2026-10-14)
- **A merge to `main` deploys.** A pull agent on Ares (systemd user timer `homelab-pull@ares`, from the owner's
  private homelab-ops repo; rolled out host by host, see Chronos) fetches `main` about every 90 s. When it moved,
  the agent fast-forwards the checkout and runs `docker compose config --quiet`, `docker compose pull` and
  `docker compose up -d --remove-orphans --wait`: a merge is live within about two minutes. It refuses local
  changes and non-fast-forward history, and moves the checkout back if config or pull fails.
- **Rollback is a revert PR**, deployed the same way. A revert doesn't undo a data migration: then the backup and
  `scripts/restore.sh` are the way back, with the owner.
- **Pinning by hand**: the owner checks out another commit or tag on the host; the agent pauses until the checkout
  is on `main` again. Release tags stay as signed, verified snapshots; they no longer drive deploys.
- **Backups and deploys take turns**: `deploy_lock` in `scripts/lib.sh` (called right after lib.sh is sourced, before
  anything stops) makes backup.sh and restore.sh wait for a running deploy (up to `deploy_lock_timeout`, 1800 s) and
  hold the agent's lock (`flock` on `<agent state root>/ares/lock`, fd 9; the agent's `flock --nonblock` skips busy
  runs); a no-op where that directory doesn't exist. Other stacks copy it with only `pull_stack` changed; tested in
  `tests/test_deploy_lock.py` (a Python `fcntl.flock` plays the agent; the real-flock cases skip on macOS).
- Ares fronts every other service in the homelab: a bad merge here takes all of them offline within minutes.

## Stack
- Docker Compose v2 (`compose.yaml`, 6 services), upstream images. Settings for directories and networks in `.env`
  (`CONFIG_ROOT`, `PROXY_NETWORK`; other kinds `*_ROOT`, `*_PATH`, `*_VOLUME`, `*_NETWORK`); the smoke test replaces
  each kind with throwaway ones, so keep that naming for new settings.
- `scripts/check_compose.py`: Python 3.14, standard library only. Reads `docker compose config --format json`,
  reports policy violations (exit 1), `--sbom FILE` writes a CycloneDX 1.6 SBOM of the images.
- `scripts/scheduled-backup.sh` (run nightly by the systemd user units in `deploy/systemd/`): backup.sh, then rsync
  to `BACKUP_REMOTE` (with `BACKUP_AGE_RECIPIENT`, only `backup.tar.age` + `SHA256SUMS`, encrypted to that age key;
  CI installs age so the smoke test covers it), pruning and an Uptime Kuma push. Its settings are in the gitignored `backup.env` (read as
  data, never sourced), not `.env`. It needs GNU rsync and macOS' openrsync alike (no `--chmod`).
- `scripts/backup.sh`, `restore.sh`, `scheduled-backup.sh`, `smoke-test.sh` (helpers in `lib.sh`): bash, must also
  run on macOS' bash 3.2 (no `mapfile`, no associative arrays).
- Tooling: ruff with every rule family (`select = ["ALL"]`, exceptions in `pyproject.toml`; per-line `noqa`
  with a reason) and `ruff format`; yamllint (`.yamllint.yml`); shellcheck (`-x`); pytest + coverage (90 %
  branch floor); pip-tools for the hash-pinned `requirements-dev.txt`. CI-only: actionlint, gitleaks, CodeQL
  (python, actions), Scorecard, dependency review, DCO, Trivy image scan, Dependabot auto-merge (patch/minor, rebuilds).
- GitLab copy: the owner's self-hosted GitLab (CE, LAN only; host facts in Chronos) holds a mirror. GitHub stays
  the home (OpenSSF badges, Scorecard, Dependabot, releases); every change goes to GitHub as a PR, never to
  GitLab. `.gitlab-ci.yml` mirrors GitHub on a schedule (fast-forward only, `MIRROR_TOKEN` CI/CD variable) and
  re-runs the daemon-free checks; the smoke test stays GitHub-only (owner 2026-10-10, as on homelab-helios).
- Releases (`release.yml`, on a `v*.*.*` tag): policy check, source archive, CycloneDX SBOM, `SHA256SUMS`
  signed with cosign keyless, SLSA provenance (Sigstore bundle + in-toto JSONL), GitHub Release from the
  tag's `CHANGELOG.md` section. No images are built or published. It refuses to run without `compose.yaml`.

## Conventions
- `CHANGELOG.md` (Keep a Changelog): add to "Unreleased" with every user-visible change.
- Docs in `docs/` change in the same PR as the behaviour; anything not built yet is marked **Planned**.
- New checker rule → fixture case that triggers it + `test_every_rule_is_reported_exactly` stays exact.
- Workflows: top-level `permissions: contents: read` (Scorecard: `read-all`), raise per job; actions pinned by
  full SHA with a version comment; untrusted `${{ github.event.* }}` only through `env:`.
- `CI / Checks + tests` and `CI / Stack smoke test` are required checks (with DCO sign-off, Dependency review and
  CodeQL's Analyze (python) / Analyze (actions)) in the `main` ruleset; don't rename those jobs.
- **Merging (owner's decisions 2026-10-07 and 2026-10-14):** Claude opens a PR for every change. A merge deploys
  (see Deploys), so Claude merges once every required check is green (the owner's standing permission, 2026-10-14) and
  then says that it merged and that it's deploying to Ares. It asks first when the deploy needs something on
  the server (a new `.env` setting, a data migration without a recent good backup, an update this file says
  waits for the owner) or the server isn't healthy, and never turns on auto-merge (`gh pr merge --auto`)
  without the owner's OK. Never bypass a check or the
  ruleset. Dependabot's patch, minor and major updates and image rebuilds still auto-merge through
  `dependabot-auto-merge.yml` once every required check passes, so they now deploy unattended; every Portainer
  update and any update Dependabot can't classify wait for the owner. Claude never merges a major update itself:
  majors are merged only by Dependabot's auto-merge or by the owner. Keeping that auto-merge is the owner's call:
  don't change `dependabot-auto-merge.yml` without it.

## Commands
```sh
make test     # checker tests + coverage floor (no Docker, no network)
make lint     # ruff check, ruff format --check, yamllint --strict, shellcheck -x
make check    # docker compose config --format json | scripts/check_compose.py  (needs .env and compose.yaml)
make smoke    # scripts/smoke-test.sh: throwaway project, healthy, backup/restore round trip (needs Docker)
make config   # docker compose config (resolved file)
```
Regenerate the dev tools: `pip-compile --generate-hashes --strip-extras requirements-dev.in`, then put the
one-line `# Generated from …` header back.

Release (only when the owner asks): move "Unreleased" into a `## [x.y.z] - date` section of `CHANGELOG.md`
(SemVer; date = the day of tagging) in a PR and merge it once green. Then, with `main` clean and equal to
`origin/main` and CI on that commit green: `git tag -s vX.Y.Z -m vX.Y.Z`, check it with
`git -c gpg.ssh.allowedSignersFile=.github/allowed_signers tag -v vX.Y.Z`, and `git push origin vX.Y.Z`;
`release.yml` does the rest. Afterwards verify the release from outside as `docs/verifying-releases.md` describes.
