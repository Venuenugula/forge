from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

from .config import get_store_dir
from .envs import get_env_site_packages, load_env_config, record_package, remove_package
from .fingerprint import generate_fingerprint, get_store_path
from .linker import link_store_into_env
from .metadata import (
    decrement_ref_count,
    find_abi_compatible_package,
    get_connection,
    get_package,
    get_package_by_name_version,
    increment_ref_count,
    init_db,
    register_package,
)
from .models import InstallReport
from .runtime import generate_pth


def parse_pkg_spec(pkg_spec: str) -> tuple[str, str]:
    if "==" in pkg_spec:
        name, version = pkg_spec.split("==", 1)
        return name.strip(), version.strip()
    return pkg_spec.strip(), "latest"


def install_to_store_with_report(
    pkg_spec: str,
    *,
    env_name: str | None = None,
    abi_policy: str = "warn_abi",
) -> InstallReport:
    name, version = parse_pkg_spec(pkg_spec)
    fingerprint = generate_fingerprint(name, version)
    store_path = get_store_path(fingerprint)
    warnings: list[str] = []
    reused = False
    reuse_kind = "fresh"

    conn = get_connection()
    try:
        init_db(conn)
        existing = get_package(conn, fingerprint)
        if existing and Path(existing["path"]).exists() and any(Path(existing["path"]).iterdir()):
            store_path = Path(existing["path"])
            reused = True
            reuse_kind = "exact"
        else:
            compatible = find_abi_compatible_package(conn, fingerprint)
            should_install = True
            if compatible and Path(compatible["path"]).exists() and any(Path(compatible["path"]).iterdir()):
                if abi_policy != "strict_abi":
                    store_path = Path(compatible["path"])
                    reused = True
                    reuse_kind = "abi_compatible"
                    should_install = False
                    if abi_policy == "warn_abi":
                        warnings.append(
                            f"ABI-compatible reuse for {name}=={version} from {store_path.name}"
                        )
            if should_install:
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
                register_package(conn, fingerprint, store_path)

        if env_name:
            env_cfg = load_env_config(env_name)
            env_python = env_cfg.get("python_version")
            runtime_python = platform.python_version()
            if env_python and env_python.split(".")[:2] != runtime_python.split(".")[:2]:
                raise RuntimeError(
                    f"Python version mismatch for env '{env_name}': "
                    f"env={env_python}, runtime={runtime_python}"
                )
            env_site_packages = get_env_site_packages(env_name)
            link_store_into_env(store_path, env_site_packages)
            increment_ref_count(conn, store_path)
            generate_pth(env_name)
    finally:
        conn.close()

    return InstallReport(path=str(store_path), reused=reused, reuse_kind=reuse_kind, warnings=warnings)


def install_to_store(
    pkg_spec: str,
    *,
    env_name: str | None = None,
    abi_policy: str = "warn_abi",
) -> Path:
    report = install_to_store_with_report(pkg_spec, env_name=env_name, abi_policy=abi_policy)
    return Path(report.path)


def install_local(pkg_spec: str, env_name: str) -> Path:
    path = install_to_store(pkg_spec, env_name=env_name)
    name, version = parse_pkg_spec(pkg_spec)
    record_package(env_name, name, version)
    return path


def uninstall_local(pkg_name: str, env_name: str) -> Path:
    env_cfg = load_env_config(env_name)
    packages = env_cfg.get("packages", {})
    if pkg_name not in packages:
        raise RuntimeError(f"Package '{pkg_name}' is not recorded as local in env '{env_name}'")
    version = packages[pkg_name]

    conn = get_connection()
    try:
        init_db(conn)
        row = get_package_by_name_version(conn, pkg_name, version)
        if row is None:
            raise RuntimeError(f"No metadata row found for {pkg_name}=={version}")
        store_path = Path(row["path"])

        site = get_env_site_packages(env_name)
        store_root = get_store_dir().resolve()
        for entry in list(site.iterdir()):
            if not entry.is_symlink():
                continue
            target = entry.resolve()
            if store_root in target.parents and store_path in target.parents:
                entry.unlink()

        decrement_ref_count(conn, store_path)
        remove_package(env_name, pkg_name)
        generate_pth(env_name)
        return store_path
    finally:
        conn.close()
