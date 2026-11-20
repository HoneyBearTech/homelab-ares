# Decisions log

Why things in homelab-ares are the way they are: each entry gives the decision, the reason, what was
considered and not done, and review findings that were declined, with why. Newest first. What shipped when
is in the [pass map](pass-map.md).

## 2026-11-20: Renovate merges its own pull requests

Job `renovate-automerge` (#91).

**Decision.** Renovate merges its pull requests itself once every check passes,
majors included; new versions wait 3 days, security fixes and image rebuilds
don't, on the model homelab-atlas already uses. Kept manual: Portainer stays
manual (its own pull request, with its agents). `platformAutomerge` is true.

**Why.** The owner asked for every repo with Renovate to merge its updates
automatically (2026-11-20) and chose this model, majors included, over keeping
majors manual.

**Not done.** Repository settings and branch rules (owner only) and workflows
are unchanged. A group merges automatically only when every update in it may, so
each manual exception gets its own pull request.

**Review findings.** Fixed: stale docs that still promised a manual review or
named Dependabot, and (where it applied) exceptions that sat inside the update
group. None declined. The upgrading guide no longer promises a manual review
before every merge.

## 2026-11-20: actionlint accepts the Ubuntu 26.04 arm runner through its config file

Job `actionlint-ubuntu-26`.

**Decision.** `.github/actionlint.yaml` lists `ubuntu-26.04-arm` under `self-hosted-runner.labels`, the
way actionlint documents for a runner name it doesn't know. Only that one name; no rule is turned off.

**Why.** Renovate's #89 moves the stack smoke test to `ubuntu-26.04-arm`. The smoke test passes there, but
actionlint 1.7.12 (newest release, March 2026) rejects the name, so "Checks + tests" failed. Both CI and
the GitLab copy run actionlint from the repository root and read the file.

**Not done.** Holding the runner at 24.04 with a Renovate rule (the newer runner works today); waiting for
a new actionlint release (none is out); editing the workflow (the owner's).

**Review findings.** None from the security review or the code audit. Both checked with the same
actionlint image CI uses: #89's workflows pass with the file and fail without it, and a misspelled name is
still reported.
