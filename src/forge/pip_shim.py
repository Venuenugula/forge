from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .envs import get_env_site_packages
from .fingerprint import generate_fingerprint, get_store_path
from .linker import link_store_into_env
from .metadata import (
    get_connection,
    increment_ref_count,
    init_db,
    register_package,
)
from .runtime import generate_pth


def parse_pkg_spec(pkg_spec: str) -> tuple[str, str]:
    if "==" in pkg_spec:
        name, version = pkg_spec.split("==", 1)
        return name.strip(), version.strip()
    return pkg_spec.strip(), "latest"


def install_to_store(
    pkg_spec: str,
    *,
    env_name: str | None = None,
) -> Path:
    name, version = parse_pkg_spec(pkg_spec)
    fingerprint = generate_fingerprint(name, version)
    store_path = get_store_path(fingerprint)
    store_path.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "pip", "install", pkg_spec, "--target", str(store_path)]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "pip install failed\n"
            f"command: {' '.join(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    if not any(store_path.iterdir()):
        raise RuntimeError(f"pip install produced no files at: {store_path}")

    conn = get_connection()
    try:
        init_db(conn)
        register_package(conn, fingerprint, store_path)

        if env_name:
            env_site_packages = get_env_site_packages(env_name)
            link_store_into_env(store_path, env_site_packages)
            increment_ref_count(conn, store_path)
            generate_pth(env_name)
    finally:
        conn.close()

    return store_path
