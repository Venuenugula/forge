from __future__ import annotations

import os
from pathlib import Path

from forge.envs import create_env, get_env_site_packages
from forge.fingerprint import generate_fingerprint, get_store_path
from forge.linker import link_store_into_env
from forge.metadata import get_connection, init_db, register_package
from forge.resolver import inspect_candidates, resolve_package
from forge.runtime import resolution_paths


def test_resolution_paths_follow_local_parent_global_order(tmp_path) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("base")
        create_env("child", parent="base")

        paths = resolution_paths("child")
        as_strings = [str(p) for p in paths]

        assert as_strings[0].endswith("/envs/child/site-packages")
        assert as_strings[1].endswith("/envs/base/site-packages")
        assert as_strings[2].endswith("/store")
    finally:
        os.environ.pop("FORGE_HOME", None)


def _seed_store_package(name: str, version: str) -> Path:
    fp = generate_fingerprint(name, version)
    root = get_store_path(fp)
    (root / name).mkdir(parents=True, exist_ok=True)
    (root / name / "__init__.py").write_text(f"__version__='{version}'\n", encoding="utf-8")
    conn = get_connection()
    try:
        init_db(conn)
        register_package(conn, fp, root)
    finally:
        conn.close()
    return root


def test_resolve_prefers_local_and_warns_on_downgrade(tmp_path) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("base")
        create_env("child", parent="base")
        base_pkg = _seed_store_package("numpy", "1.26.4")
        child_pkg = _seed_store_package("numpy", "1.20.0")
        link_store_into_env(base_pkg, get_env_site_packages("base"))
        link_store_into_env(child_pkg, get_env_site_packages("child"))

        result = resolve_package("numpy", "child", mode="warn")
        assert result.source == "local"
        assert result.version == "1.20.0"
        assert len(result.warnings) == 1
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_resolve_strict_raises_on_local_parent_conflict(tmp_path) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("base")
        create_env("child", parent="base")
        base_pkg = _seed_store_package("numpy", "1.26.4")
        child_pkg = _seed_store_package("numpy", "1.20.0")
        link_store_into_env(base_pkg, get_env_site_packages("base"))
        link_store_into_env(child_pkg, get_env_site_packages("child"))

        raised = False
        try:
            resolve_package("numpy", "child", mode="strict")
        except RuntimeError:
            raised = True
        assert raised
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_inspect_candidates_reports_layer_presence(tmp_path) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("base")
        create_env("child", parent="base")
        base_pkg = _seed_store_package("numpy", "1.26.4")
        link_store_into_env(base_pkg, get_env_site_packages("base"))

        candidates = inspect_candidates("numpy", "child")
        assert candidates.local.exists is False
        assert len(candidates.parents) == 1
        assert candidates.parents[0].env == "base"
        assert candidates.parents[0].exists is True
        assert "1.26.4" in candidates.global_versions
    finally:
        os.environ.pop("FORGE_HOME", None)
