# Pass map

A short record of each piece of work on homelab-ares: what shipped, or what a review found, and where to
look. Newest first. The reasons behind the choices are in the [decisions log](decisions-log.md); what is
planned next is in the [roadmap](roadmap.md).

| Date | Job | What shipped or was found | Where |
| --- | --- | --- | --- |
| 2026-11-20 | `actionlint-ubuntu-26` | `.github/actionlint.yaml` lists `ubuntu-26.04-arm` as an accepted runner name, so Renovate's #89 (the stack smoke test on the Ubuntu 26.04 arm runner) no longer fails the workflow lint: actionlint 1.7.12, the newest release, doesn't know that name. One sentence in `CONTRIBUTING.md`. Security review clear, code audit approved. #88 (11 minor and patch updates) merged by the owner the same day. | This pull request; `docs/plans/actionlint-ubuntu-26.md` |
