"""Tests for deploy_lock in scripts/lib.sh: backup.sh and restore.sh take turns with the pull agent's deploys.

Each test runs bash with `set -euo pipefail` (as the scripts do), sources lib.sh and calls deploy_lock, with HOME and
the agent's state root in a temporary directory. A Python fcntl.flock on the lock file stands in for the agent (the
agent's `flock --nonblock` uses the same flock(2) lock). The cases that need the flock command skip where it isn't
installed (macOS).
"""

import fcntl
import os
import shutil
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import IO, TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

LIB = Path(__file__).parent.parent / "scripts" / "lib.sh"
BASH = shutil.which("bash") or "/bin/bash"
needs_flock = pytest.mark.skipif(
    shutil.which("flock") is None, reason="flock isn't installed (util-linux; not on macOS)"
)


def environment(home: Path, **extra: str) -> dict[str, str]:
    """The test's environment: HOME in the temporary directory, no state root set unless `extra` sets one."""
    env = {k: v for k, v in os.environ.items() if k not in {"HOMELAB_PULL_STATE_DIR", "XDG_STATE_HOME"}}
    return {**env, "HOME": str(home), **extra}


def argv(script: str) -> list[str]:
    """Bash running `script` after sourcing lib.sh, as backup.sh and restore.sh do."""
    return [BASH, "-c", f'set -euo pipefail\n. "$1"\n{script}', "bash", str(LIB)]


def run(script: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    # S603: fixed argv, no shell; the script text is the test's own.
    return subprocess.run(argv(script), env=env, capture_output=True, text=True, check=False, timeout=30)  # noqa: S603


def start(script: str, env: dict[str, str]) -> subprocess.Popen[str]:
    """Start `script` as run() does, in the background, with its stdin a pipe the test closes to end a `read`."""
    pipe = subprocess.PIPE
    # S603: as in run().
    return subprocess.Popen(argv(script), env=env, stdin=pipe, stdout=pipe, stderr=pipe, text=True)  # noqa: S603


def stack_dir(state: Path, home: Path) -> Path:
    """Create the agent's state directory for this stack (pull_stack in lib.sh) under `state`."""
    out = run('printf %s "$pull_stack"', environment(home))
    assert out.returncode == 0, out.stderr
    path = state / out.stdout
    path.mkdir(parents=True)
    return path


@contextmanager
def agent_deploying(lock: Path) -> Iterator[IO[bytes]]:
    """The pull agent mid-deploy: holds `lock` until the block ends (or the file is closed early)."""
    with lock.open("ab") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield f


def is_locked(lock: Path) -> bool:
    """What the agent's `flock --nonblock` would find: True when someone else holds `lock`."""
    with lock.open("ab") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False


def read_line(proc: subprocess.Popen[str]) -> str:
    assert proc.stdout is not None
    return proc.stdout.readline()


@pytest.mark.parametrize("variable", ["HOMELAB_PULL_STATE_DIR", "XDG_STATE_HOME", None])
def test_no_agent_state_does_nothing(tmp_path: Path, variable: str | None) -> None:
    home = tmp_path / "home"
    home.mkdir()
    extra = {variable: str(tmp_path / "state")} if variable else {}
    out = run("deploy_lock\necho ran", environment(home, **extra))
    assert (out.returncode, out.stdout, out.stderr) == (0, "ran\n", "")
    # Nothing was created: not the state root, not the stack's directory, not a lock file.
    assert not (tmp_path / "state").exists()
    assert list(home.iterdir()) == []


def test_agent_state_without_flock_fails_before_anything_runs(tmp_path: Path) -> None:
    dir_ = stack_dir(tmp_path / "state", tmp_path)
    empty = tmp_path / "bin"
    empty.mkdir()
    env = environment(tmp_path, HOMELAB_PULL_STATE_DIR=str(tmp_path / "state"), PATH=str(empty))
    out = run("deploy_lock\necho ran", env)
    assert out.returncode == 1
    assert out.stdout == ""
    assert out.stderr == f"error: {dir_} exists (the pull agent deploys here) but flock isn't installed to lock it\n"
    assert list(dir_.iterdir()) == []


@needs_flock
@pytest.mark.parametrize("variable", ["HOMELAB_PULL_STATE_DIR", "XDG_STATE_HOME"])
def test_lock_is_held_until_the_script_exits(tmp_path: Path, variable: str) -> None:
    state = tmp_path / "state"
    lock = stack_dir(state if variable == "HOMELAB_PULL_STATE_DIR" else state / "homelab-pull", tmp_path) / "lock"
    # The script stops at `read` until the test closes its stdin, then exits.
    proc = start("deploy_lock\necho locked\nread -r _ || true", environment(tmp_path, **{variable: str(state)}))
    assert read_line(proc) == "locked\n"
    time.sleep(0.2)
    assert is_locked(lock)  # the agent's run now finds the lock busy and skips
    stdout, stderr = proc.communicate(timeout=30)
    assert (proc.returncode, stdout, stderr) == (0, "", "")
    assert not is_locked(lock)  # and its next run after the script exited can deploy


@needs_flock
def test_waits_for_a_running_deploy_then_runs(tmp_path: Path) -> None:
    lock = stack_dir(tmp_path / "state", tmp_path) / "lock"
    env = environment(tmp_path, HOMELAB_PULL_STATE_DIR=str(tmp_path / "state"))
    with agent_deploying(lock) as deploy:
        proc = start("deploy_lock\necho ran", env)
        assert read_line(proc) == "Waiting for a deploy by the pull agent to finish (up to 1800 s)\n"
        time.sleep(0.3)
        assert proc.poll() is None  # still waiting: nothing after deploy_lock has run
        deploy.close()  # the deploy finishes
        stdout, stderr = proc.communicate(timeout=30)
    assert (proc.returncode, stdout, stderr) == (0, "ran\n", "")


@needs_flock
def test_times_out_with_an_error_and_runs_nothing_after(tmp_path: Path) -> None:
    dir_ = stack_dir(tmp_path / "state", tmp_path)
    env = environment(tmp_path, HOMELAB_PULL_STATE_DIR=str(tmp_path / "state"))
    with agent_deploying(dir_ / "lock"):
        out = run("deploy_lock_timeout=1\ndeploy_lock\necho ran", env)
    assert out.returncode == 1
    assert out.stdout == "Waiting for a deploy by the pull agent to finish (up to 1 s)\n"
    stack = dir_.name
    assert out.stderr == (
        f"error: the pull agent's deploy of {stack} still holds {dir_}/lock after 1 s; nothing was stopped"
        f" (check: journalctl --user -u homelab-pull@{stack})\n"
    )
