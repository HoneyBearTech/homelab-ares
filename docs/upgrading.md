# Upgrading

A homelab-ares release changes which image versions run, and sometimes the services or settings. Services often
migrate their database when they start a new version and can't go back afterwards, so **every upgrade starts
with a backup**. The same steps apply to updating a checkout of `main`, which is possible but unsupported for
anything you depend on.

## Before you upgrade

1. Read the release notes (the `CHANGELOG.md` section) for every release between yours and the new one, and
   the services' own release notes for any major version bump. Anything under **Upgrading** needs action.
2. Verify the new release ([verifying-releases.md](verifying-releases.md)).
3. Plan for the proxy being down for a minute or two: every service behind it is unreachable meanwhile.

## Backing up

The state worth keeping is each service's data: every read-write volume or directory it mounts (the proxy's
settings and certificates, Uptime Kuma's database, PeaNUT's settings, Portainer's database). `scripts/backup.sh`
stops one service at a time, archives its mounts while it is stopped so its database is consistent, and starts it
again if it was running; services with nothing to archive keep running. It also copies `.env` and any
`<service>.env` (such as `autoheal.env`):

```sh
scripts/backup.sh                       # into backups/<date>-<time>/ in the checkout (gitignored)
scripts/backup.sh /path/to/backup-dir   # or a directory of your choice (new or empty)
```

The directory holds one `<service>--<path>.tar.gz` per mount (for example `npm--etc_letsencrypt.tar.gz`), the
settings under `env/`, a `MANIFEST` naming each archive's service, container path, volume or host path and
image, and `SHA256SUMS`. Everything in it is readable only by the user who ran the backup. **Copy it off the
host**: it contains the certificates' private keys and every service's logins. Every service needs a container
for the backup to read from, so run it on an installed stack. The Docker socket and anonymous volumes are never
archived. [Scheduled backups](installing.md#scheduled-backups) do this nightly and copy each backup off the host.

## Upgrading

```sh
git fetch --tags
git checkout vX.Y.Z
docker compose pull
docker compose up -d --wait
docker compose ps
```

Then check each service's web UI and logs (`docker compose logs <service>`) for migration errors, and that a
few proxied services still answer through the proxy.

## Rolling back

If a service fails after the upgrade, go back to the previous version **and** restore its data; a service whose
database was migrated forward may not start with the older image. For one service (Uptime Kuma here):

```sh
git checkout vPREVIOUS
scripts/restore.sh backups/YYYYMMDD-HHMMSS uptime-kuma   # checks SHA256SUMS, lists what it replaces, asks first
docker compose up -d uptime-kuma
```

`scripts/restore.sh` replaces everything in each of the service's mounts listed in the backup's `MANIFEST`,
keeping the files' owners and modes. Without service names it restores every service in the backup. It stops
those services while it works and starts again the ones that were running; `--yes` skips the question.

## Restoring on a new host

See [rebuilding.md](rebuilding.md): install the host, restore `.env`, then `scripts/restore.sh` creates the
volumes and containers and fills them from the backup.
