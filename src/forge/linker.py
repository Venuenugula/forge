from __future__ import annotations

from pathlib import Path


def link_package(src: Path, dest: Path) -> Path:
    src = src.resolve()
    if not src.exists():
        raise FileNotFoundError(f"Cannot link missing source: {src}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink() and dest.resolve() == src:
            return dest
        raise FileExistsError(f"Destination already exists and conflicts: {dest}")

    dest.symlink_to(src, target_is_directory=src.is_dir())
    return dest


def link_store_into_env(store_path: Path, env_site_packages: Path) -> list[Path]:
    if not store_path.exists():
        raise FileNotFoundError(f"Store path does not exist: {store_path}")

    env_site_packages.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    for entry in sorted(store_path.iterdir()):
        dest = env_site_packages / entry.name
        linked = link_package(entry, dest)
        created.append(linked)

    return created
