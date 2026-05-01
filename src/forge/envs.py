from __future__ import annotations

import json
import platform
from pathlib import Path

from .config import ensure_dirs, get_envs_dir


def get_env_path(name: str) -> Path:
    return get_envs_dir() / name


def get_env_config_path(name: str) -> Path:
    return get_env_path(name) / "config.json"


def get_env_site_packages(name: str) -> Path:
    return get_env_path(name) / "site-packages"


def create_env(name: str, parent: str | None = None, python_version: str | None = None) -> Path:
    ensure_dirs()
    env_path = get_env_path(name)
    env_path.mkdir(parents=True, exist_ok=True)
    get_env_site_packages(name).mkdir(parents=True, exist_ok=True)

    if parent:
        # Fail fast if parent environment does not exist.
        if not get_env_config_path(parent).exists():
            raise ValueError(f"Parent environment does not exist: {parent}")

    config = {
        "name": name,
        "parent": parent,
        "python_version": python_version or platform.python_version(),
        "packages": {},
        "settings": {
            "abi_policy": "warn_abi",
        },
    }
    with get_env_config_path(name).open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    _assert_no_cycle(name)
    return env_path


def load_env_config(name: str) -> dict:
    config_path = get_env_config_path(name)
    if not config_path.exists():
        raise ValueError(f"Environment does not exist: {name}")
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_env_config(name: str, config: dict) -> None:
    config_path = get_env_config_path(name)
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def record_package(name: str, pkg_name: str, version: str) -> None:
    config = load_env_config(name)
    packages = config.setdefault("packages", {})
    packages[pkg_name] = version
    save_env_config(name, config)


def remove_package(name: str, pkg_name: str) -> None:
    config = load_env_config(name)
    packages = config.setdefault("packages", {})
    if pkg_name in packages:
        del packages[pkg_name]
    save_env_config(name, config)


def list_env_names() -> list[str]:
    ensure_dirs()
    envs_dir = get_envs_dir()
    names: list[str] = []
    for entry in sorted(envs_dir.iterdir()):
        if entry.is_dir() and (entry / "config.json").exists():
            names.append(entry.name)
    return names


def get_env_setting(name: str, key: str, default: str | None = None) -> str | None:
    config = load_env_config(name)
    settings = config.get("settings", {})
    return settings.get(key, default)


def set_env_setting(name: str, key: str, value: str) -> None:
    config = load_env_config(name)
    settings = config.setdefault("settings", {})
    settings[key] = value
    save_env_config(name, config)


def get_all_env_settings(name: str) -> dict:
    config = load_env_config(name)
    return dict(config.get("settings", {}))


def parent_chain(name: str) -> list[str]:
    """Return parent-first chain (direct parent, grandparent, ...)."""
    chain: list[str] = []
    seen: set[str] = set()
    current = name
    while True:
        cfg = load_env_config(current)
        parent = cfg.get("parent")
        if not parent:
            break
        if parent in seen or parent == name:
            raise ValueError(f"Circular parent chain detected for environment: {name}")
        chain.append(parent)
        seen.add(parent)
        current = parent
    return chain


def _assert_no_cycle(name: str) -> None:
    # parent_chain raises if a cycle exists.
    parent_chain(name)
