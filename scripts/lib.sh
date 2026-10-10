# Helpers shared by backup.sh, restore.sh and smoke-test.sh, which source this file; it isn't run on its own.
# Written for bash 3.2 and later (macOS ships 3.2).
# shellcheck shell=bash

# Reads and writes the services' data in throwaway containers; pinned like every other image (bumped by hand, see
# docs/dependencies.md).
# shellcheck disable=SC2034 # used by the scripts that source this file
busybox=busybox:1.38.0@sha256:fd7dc98638c8e305f4dc34e979f1c0fdfdcaeb0fbf8fcff77ae834b6da3d7e6e

sha256() { if command -v sha256sum >/dev/null; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }

# The data mounts of container $1, one "<container path><TAB><volume:NAME or host path>" per line: every read-write
# volume or bind mount, except anonymous volumes (an image's own, holding nothing the stack set up) and the Docker
# socket. These are what a backup archives and a restore replaces.
data_mounts() {
  local dest source
  docker inspect --format '{{range .Mounts}}{{if and .RW (or (eq .Type "volume") (eq .Type "bind"))}}'\
'{{.Destination}}{{"\t"}}{{if .Name}}volume:{{.Name}}{{else}}{{.Source}}{{end}}{{"\n"}}{{end}}{{end}}' "$1" |
    while IFS=$'\t' read -r dest source; do
      if [ -z "$dest" ] || [[ "$source" =~ ^volume:[0-9a-f]{64}$ ]]; then continue; fi
      if [[ "$dest" == *docker.sock || "$source" == *docker.sock ]]; then continue; fi
      printf '%s\t%s\n' "$dest" "$source"
    done
}

# What container $1 leaves out of its backups, one "<mount><TAB><name>" per line: its label
# org.honeybeartech.ares.backup.exclude lists container paths (separated by spaces), each an entry directly inside
# one of its data mounts, such as /data/logs (mount /data, name logs). A backup doesn't archive them and a restore
# leaves them as they are. Any other path is an error, so a typo can't quietly change what is backed up.
backup_excludes() {
  local value path mount name found mounts
  local -a paths=()
  value=$(docker inspect --format '{{index .Config.Labels "org.honeybeartech.ares.backup.exclude"}}' "$1")
  read -r -a paths <<<"$value"
  mounts=$(data_mounts "$1" | cut -f1)
  for path in "${paths[@]+"${paths[@]}"}"; do
    found=false
    while IFS= read -r mount; do
      name=${path#"$mount"/}
      if [ -n "$mount" ] && [ "$name" != "$path" ] && [[ "$name" =~ ^[A-Za-z0-9_@-][A-Za-z0-9_.@-]*$ ]]; then
        printf '%s\t%s\n' "$mount" "$name"
        found=true
      fi
    done <<<"$mounts"
    if ! $found; then
      echo "error: org.honeybeartech.ares.backup.exclude: $path isn't an entry directly inside a data mount" >&2
      return 1
    fi
  done
}

# Whether $2 is a directory in container $1 (a bind-mounted file isn't archived).
is_dir() { docker run --rm --network none --volumes-from "$1:ro" "$busybox" test -d "$2" </dev/null; }

# The archive name for service $1's mount at $2: <service>--<container path, / as _>.tar.gz
archive_name() {
  local path=${2#/}
  printf '%s--%s.tar.gz' "$1" "${path//\//_}"
}
