import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
CONFIG_ROOT = "${CONFIG_ROOT:?set CONFIG_ROOT in .env}"
# Each app's data mounts, as "<folder under CONFIG_ROOT/<app>>:<container path>"; the first is its config directory.
APPS = {
    "npm": ("config:/data", "letsencrypt:/etc/letsencrypt", "logrotate:/var/lib/logrotate"),
    "uptime-kuma": ("config:/app/data",),
    "peanut": ("config:/config",),
    "portainer": ("config:/data",),
}
SOCKET = "/var/run/docker.sock:/var/run/docker.sock"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def compose() -> dict:
    return yaml.safe_load(read("compose.yaml"))


def test_every_setting_is_in_env_example_and_interfaces() -> None:
    used = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", read("compose.yaml")))
    example = set(re.findall(r"^([A-Z][A-Z0-9_]*)=", read(".env.example"), re.MULTILINE))
    table = re.findall(r"^\| (`[A-Z][^|]*) \|", read("docs/interfaces.md"), re.MULTILINE)
    documented = {name for cell in table for name in re.findall(r"`([A-Z][A-Z0-9_]*)`", cell)}
    assert used == example
    assert used <= documented


def test_each_app_keeps_its_data_in_its_folder_under_config_root() -> None:
    services = compose()["services"]
    for app, mounts in APPS.items():
        volumes = [volume for volume in services[app]["volumes"] if not volume.startswith(SOCKET)]
        assert volumes == [f"{CONFIG_ROOT}/{app}/{mount}" for mount in mounts]


def test_every_service_with_data_is_an_app() -> None:
    for name, service in compose()["services"].items():
        data = [volume for volume in service.get("volumes") or [] if not volume.startswith(SOCKET)]
        assert not data or name in APPS, f"{name} mounts data outside CONFIG_ROOT/<app>: {data}"


def test_no_named_volumes() -> None:
    config = compose()
    assert "volumes" not in config
    for name, service in config["services"].items():
        for volume in service.get("volumes") or []:
            assert volume.startswith(("/", "${")), f"{name} mounts a named volume: {volume}"


def test_no_setting_points_into_dockers_volumes() -> None:
    for line in read(".env.example").splitlines():
        assert "/var/lib/docker" not in line.partition("#")[0], line
