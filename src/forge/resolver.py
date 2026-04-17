from __future__ import annotations

import sys
from pathlib import Path

from .config import get_store_dir
from .envs import get_env_site_packages, parent_chain
from .metadata import get_connection, init_db, list_packages
from .models import CandidateEntry, InspectCandidates, ResolveResult


def detect_mode() -> str:
    return "warn" if sys.stdout.isatty() else "strict"


def _package_version_from_site_path(pkg_path: Path) -> str | None:
    resolved = pkg_path.resolve()
    store_dir = get_store_dir().resolve()
    if store_dir not in resolved.parents:
        return None
    parts = resolved.parts
    try:
        store_idx = parts.index("store")
    except ValueError:
        return None
    if len(parts) <= store_idx + 2:
        return None
    # /.../store/<name>/<version>/<leaf>/<import_name>
    return parts[store_idx + 2]


def _global_versions(pkg_name: str) -> list[str]:
    conn = get_connection()
    try:
        init_db(conn)
        versions = [row["version"] for row in list_packages(conn) if row["name"] == pkg_name]
        return sorted(set(versions))
    finally:
        conn.close()


def inspect_candidates(pkg_name: str, env_name: str) -> InspectCandidates:
    local_path = get_env_site_packages(env_name) / pkg_name
    local_entry = CandidateEntry(
        exists=local_path.exists(),
        version=_package_version_from_site_path(local_path) if local_path.exists() else None,
        path=str(local_path),
    )

    parents: list[CandidateEntry] = []
    for parent in parent_chain(env_name):
        candidate = get_env_site_packages(parent) / pkg_name
        parents.append(
            CandidateEntry(
                env=parent,
                exists=candidate.exists(),
                version=_package_version_from_site_path(candidate) if candidate.exists() else None,
                path=str(candidate),
            )
        )

    global_versions = _global_versions(pkg_name)
    return InspectCandidates(local=local_entry, parents=parents, global_versions=global_versions)


def resolve_package(pkg_name: str, env_name: str, mode: str | None = None) -> ResolveResult:
    resolved_mode = mode or detect_mode()
    warnings: list[str] = []

    local_path = get_env_site_packages(env_name) / pkg_name
    local_exists = local_path.exists()
    local_version = _package_version_from_site_path(local_path) if local_exists else None

    parent_found: tuple[str, str | None] | None = None
    for parent in parent_chain(env_name):
        candidate = get_env_site_packages(parent) / pkg_name
        if candidate.exists():
            parent_found = (parent, _package_version_from_site_path(candidate))
            break

    global_versions = _global_versions(pkg_name)
    global_version = global_versions[-1] if global_versions else None

    if local_exists:
        if parent_found and parent_found[1] and local_version and parent_found[1] != local_version:
            msg = (
                f"{pkg_name} downgraded: {parent_found[1]} (parent:{parent_found[0]}) "
                f"-> {local_version} (local:{env_name})"
            )
            if resolved_mode == "strict":
                raise RuntimeError(msg)
            if resolved_mode == "warn":
                warnings.append(msg)
        return ResolveResult(source="local", version=local_version, warnings=warnings)

    if parent_found:
        return ResolveResult(source=f"parent:{parent_found[0]}", version=parent_found[1], warnings=warnings)

    if global_version:
        return ResolveResult(source="global", version=global_version, warnings=warnings)

    raise RuntimeError(f"Package not found in local/parent/global layers: {pkg_name}")
