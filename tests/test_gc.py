from __future__ import annotations

import os

from forge.envs import create_env, get_env_site_packages
from forge.fingerprint import generate_fingerprint, get_store_path
from forge.gc import gc_dry_run
from forge.linker import link_store_into_env
from forge.metadata import get_connection, init_db, register_package


def _seed_store_package(name: str, version: str, size: int = 16) -> None:
    fp = generate_fingerprint(name, version)
    root = get_store_path(fp)
    (root / name).mkdir(parents=True, exist_ok=True)
    (root / name / "__init__.py").write_text("x" * size, encoding="utf-8")
    conn = get_connection()
    try:
        init_db(conn)
        register_package(conn, fp, root)
    finally:
        conn.close()


def test_gc_dry_run_reports_only_unlinked_store_packages(tmp_path) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("ml")
        _seed_store_package("numpy", "1.26.4", size=128)
        _seed_store_package("pandas", "2.2.1", size=64)

        numpy_root = get_store_path(generate_fingerprint("numpy", "1.26.4"))
        link_store_into_env(numpy_root, get_env_site_packages("ml"))

        result = gc_dry_run()
        names = {(row.name, row.version) for row in result.unused}
        assert ("pandas", "2.2.1") in names
        assert ("numpy", "1.26.4") not in names
        assert result.reclaimable_bytes > 0
    finally:
        os.environ.pop("FORGE_HOME", None)
