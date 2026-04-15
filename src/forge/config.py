from __future__ import annotations

import os
from pathlib import Path

FORGE_HOME_ENV = "FORGE_HOME"


def get_forge_home() -> Path:
    """Return Forge home, allowing tests to override via FORGE_HOME."""
    raw = os.environ.get(FORGE_HOME_ENV)
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / ".forge").resolve()


def get_store_dir() -> Path:
    return get_forge_home() / "store"


def get_envs_dir() -> Path:
    return get_forge_home() / "envs"


def get_db_path() -> Path:
    return get_forge_home() / "metadata.db"


def ensure_dirs() -> None:
    forge_home = get_forge_home()
    store_dir = get_store_dir()
    envs_dir = get_envs_dir()

    forge_home.mkdir(parents=True, exist_ok=True)
    store_dir.mkdir(parents=True, exist_ok=True)
    envs_dir.mkdir(parents=True, exist_ok=True)
