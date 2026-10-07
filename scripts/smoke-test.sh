#!/usr/bin/env bash
# Smoke test of the stack: start every service in compose.yaml with throwaway settings, wait until each one reports
# healthy, then mark every data mount, take a backup, change the data, restore the backup and check that the data
# and health came back, and remove everything it created. CI runs it on every change; `make smoke` runs it locally.
# Without a compose.yaml there is nothing to test, and it says so and passes.
#
# It stays away from any real installation on the same Docker host: its own Compose project, settings from
# .env.example with every directory (*_ROOT, *_PATH) moved into a temporary directory and every name prefix
# (*_PREFIX) set to the project's, no fixed container names, no published ports and no service env files. It never
# reads .env, ignores the stack's settings in the environment, and on exit removes only the volumes Compose
# labelled with its own project.
set -euo pipefail

project=homelab-ares-smoke
timeout=${SMOKE_TIMEOUT:-300}
root=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=scripts/lib.sh
. "$root/scripts/lib.sh"

if [ ! -f "$root/compose.yaml" ]; then
  message="No compose.yaml yet; nothing to smoke-test"
  if [ -n "${GITHUB_ACTIONS:-}" ]; then echo "::notice::$message"; else echo "$message"; fi
  exit 0
fi
work=$(mktemp -d)

# The settings come from the generated env file only, never from the caller's environment. The Compose variables
# also point scripts/backup.sh and scripts/restore.sh at this project.
settings=$(grep -E '^[A-Z][A-Z0-9_]*=' "$root/.env.example" || true)
while IFS='=' read -r key _; do
  if [ -n "$key" ]; then unset "$key"; fi
done <<<"$settings"
unset COMPOSE_PROFILES
export COMPOSE_PROJECT_NAME=$project
export COMPOSE_FILE=$root/compose.yaml:$work/override.yaml
export COMPOSE_ENV_FILES=$work/env

compose() { docker compose "$@"; }

cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    compose ps --all || true
    compose logs --no-color --tail 50 || true
  fi
  compose down --remove-orphans --timeout 30 || true
  docker volume ls -q --filter "label=com.docker.compose.project=$project" |
    xargs -r docker volume rm >/dev/null || true
  rm -rf "$work"
  exit "$status"
}
trap cleanup EXIT

while IFS= read -r line; do
  [ -n "$line" ] || continue
  key=${line%%=*}
  case $key in
    *_ROOT | *_PATH)
      value=$work/$(echo "$key" | tr 'A-Z_' 'a-z-')
      mkdir -p "$value"
      ;;
    *_PREFIX) value=${project}_ ;;
    *) value=${line#*=} ;;
  esac
  printf '%s=%s\n' "$key" "$value"
done <<<"$settings" >"$work/env"

# Project-scoped container names, no published ports and no env files, so the test can't collide with anything
# already running on the host or read a real secret; the health checks run inside the containers and need neither.
{
  echo "services:"
  for service in $(COMPOSE_FILE=$root/compose.yaml docker compose config --no-interpolate --services); do
    printf '  %s:\n    container_name: !reset null\n    ports: !reset []\n    env_file: !reset []\n' "$service"
  done
} >"$work/override.yaml"

compose config --quiet
echo "Starting $(compose config --services | wc -l | tr -d ' ') services, waiting up to ${timeout}s for them to be healthy"
# One retry: a service that fetches something from the internet as it starts can fail on the network, not the
# stack. A service that is really broken fails both attempts.
if ! compose up --detach --quiet-pull --wait --wait-timeout "$timeout"; then
  echo "Not every service became healthy; retrying once"
  compose up --detach --wait --wait-timeout "$timeout"
fi
compose ps --format 'table {{.Service}}\t{{.Status}}'

fail() {
  echo "error: $*" >&2
  exit 1
}

# A marker file in a data mount, written and read in a throwaway container (the service's image may have no shell).
put_marker() {
  docker run --rm --network none --volumes-from "$1" "$busybox" \
    sh -c 'echo "$2" >"$1/.smoke-marker" && if [ "$2" = changed ]; then touch "$1/.smoke-stray"; fi' \
    marker "$2" "$3" </dev/null
}
check_marker() {
  docker run --rm --network none --volumes-from "$1:ro" "$busybox" \
    sh -c 'test "$(cat "$1/.smoke-marker")" = backed-up && test ! -e "$1/.smoke-stray"' check "$2" </dev/null
}

# Every directory a backup would archive, as "<service><TAB><mount>".
targets=()
for service in $(compose config --services); do
  id=$(compose ps --all --quiet "$service")
  while IFS=$'\t' read -r mount _; do
    if is_dir "$id" "$mount"; then targets+=("$service	$mount"); fi
  done < <(data_mounts "$id")
done
if [ ${#targets[@]} -eq 0 ]; then
  echo "No service has a data mount; skipping the backup and restore round trip"
  exit 0
fi

echo "Backup and restore round trip over ${#targets[@]} data mount(s)"
for target in "${targets[@]}"; do
  IFS=$'\t' read -r service mount <<<"$target"
  put_marker "$(compose ps --quiet "$service")" "$mount" backed-up
done
"$root/scripts/backup.sh" "$work/backup"
[ "$(compose ps --services --status running | wc -l)" -eq "$(compose config --services | wc -l)" ] ||
  fail "backup.sh didn't start every service again"

for target in "${targets[@]}"; do
  IFS=$'\t' read -r service mount <<<"$target"
  put_marker "$(compose ps --quiet "$service")" "$mount" changed
done
"$root/scripts/restore.sh" --yes "$work/backup"

for target in "${targets[@]}"; do
  IFS=$'\t' read -r service mount <<<"$target"
  check_marker "$(compose ps --all --quiet "$service")" "$mount" ||
    fail "$service $mount wasn't restored exactly (marker changed, or a file not in the backup was left)"
done
compose up --detach --wait --wait-timeout "$timeout"
echo "Every data mount was restored, and every service is healthy again"
