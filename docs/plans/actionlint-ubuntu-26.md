# Plan: let the workflow linter accept the Ubuntu 26.04 arm runner

**What Sean asked for:** "work all open PRs in homelab-ares".

## What we found

- **#88** (Renovate's group of 11 minor and patch updates) is green on every check. It updates three images
  that run on ares (Nginx Proxy Manager 2.17.1, Portainer 2.45.4, socket-proxy 3.4.8), so merging it
  deploys them. Nothing to change in it.
- **#89** (Renovate: the stack smoke test's runner from `ubuntu-24.04-arm` to `ubuntu-26.04-arm`) fails
  "Checks + tests" at the workflow lint step only. The smoke test itself passes on the new runner.
  actionlint 1.7.12, the newest release (March 2026), stops at
  `label "ubuntu-26.04-arm" is unknown`: its list of GitHub's runner names predates 26.04.
- actionlint reads an optional config file, `.github/actionlint.yaml`, whose `self-hosted-runner.labels`
  list adds runner names it should accept. This is its documented way to accept a runner name it doesn't
  know yet. Both CI and the GitLab copy run actionlint from the repository root, so both read the file.
- The team may not edit workflow files; this config file is not one.

## What we'll change

1. **New file `.github/actionlint.yaml`** listing `ubuntu-26.04-arm` as an accepted runner name, with a
   comment saying why and that it can go once actionlint knows the name.
   *Checked by:* actionlint 1.7.12 (the same image and digest CI uses) passes on #89's version of the
   workflows with the file, and fails without it; it still passes on `main`'s workflows.
2. **A line in `CONTRIBUTING.md`** where it describes actionlint, saying the config file exists and why.
   *Checked by:* review.
3. **After the owner merges this**, #89's "Checks + tests" is run again (closing and reopening #89, or
   Renovate's next rebase) and passes. *Checked by:* the checks on #89.

## Who's on it

Team lead, Engineer, Security Officer, code auditor.

## Risks

- The file tells actionlint to accept that runner name without checking it. A typo in a future workflow
  that happens to match it exactly is the only thing it could hide; GitHub itself rejects a runner name
  that doesn't exist.
- Merging #89 moves the smoke test to a newer Ubuntu. Its own run on that runner passes.

## Out of scope

- Merging #88 and #89 (the owner merges; #88 deploys image updates to ares).
- Pinning actionlint to a newer version: there is none yet.
- The repo has no guidelines file; adding one is a separate job.
