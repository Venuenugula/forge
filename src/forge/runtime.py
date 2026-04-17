from __future__ import annotations

from pathlib import Path
import shlex

from .config import get_store_dir
from .envs import get_env_site_packages, parent_chain


def resolution_paths(env_name: str) -> list[Path]:
    paths: list[Path] = [get_env_site_packages(env_name)]
    for parent in parent_chain(env_name):
        paths.append(get_env_site_packages(parent))
    paths.append(get_store_dir())
    return paths


def generate_pth(env_name: str, paths: list[Path] | None = None) -> Path:
    pth_path = get_env_site_packages(env_name) / "forge_layers.pth"
    pth_path.parent.mkdir(parents=True, exist_ok=True)

    selected = paths or resolution_paths(env_name)
    with pth_path.open("w", encoding="utf-8") as f:
        for p in selected:
            f.write(f"{p}\n")
    return pth_path


def activation_exports(env_name: str) -> str:
    """
    Return shell export commands for deterministic runtime path layering.
    Usage:
      eval "$(forge activate <env>)"
    """
    joined = ":".join(str(p) for p in resolution_paths(env_name))
    quoted = shlex.quote(joined)
    env_quoted = shlex.quote(env_name)
    return (
        f"export FORGE_ACTIVE_ENV={env_quoted}\n"
        f"export PYTHONPATH={quoted}${{PYTHONPATH:+:$PYTHONPATH}}"
    )
