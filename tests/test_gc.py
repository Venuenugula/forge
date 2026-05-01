from __future__ import annotations

import os

from forge.envs import create_env, get_env_site_packages
from forge.fingerprint import generate_fingerprint, get_store_path
from forge.gc import doctor_check, doctor_fix, gc_apply, gc_dry_run
from forge.linker import link_store_into_env
from forge.metadata import get_connection, init_db, list_packages, register_package


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


def test_gc_apply_deletes_unused_and_metadata_rows(tmp_path) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        _seed_store_package("orphan", "0.1.0", size=32)
        root = get_store_path(generate_fingerprint("orphan", "0.1.0"))
        assert root.exists()

        report = gc_apply(force=True)
        assert any(item.name == "orphan" for item in report.unused)
        assert not root.exists()

        conn = get_connection()
        try:
            init_db(conn)
            rows = list_packages(conn)
            assert all(row["name"] != "orphan" for row in rows)
        finally:
            conn.close()
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_doctor_reports_missing_metadata_and_broken_symlink(tmp_path) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        _seed_store_package("ghost", "9.9.9", size=8)
        ghost_root = get_store_path(generate_fingerprint("ghost", "9.9.9"))
        # Leave metadata row but remove files to simulate corruption.
        import shutil

        shutil.rmtree(ghost_root)

        create_env("ml")
        broken_target = tmp_path / "missing_target"
        broken_link = get_env_site_packages("ml") / "broken_pkg"
        broken_link.symlink_to(broken_target)

        report = doctor_check()
        assert report.ok is False
        kinds = {issue.kind for issue in report.issues}
        assert "metadata_missing_path" in kinds
        assert "broken_symlink" in kinds
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_doctor_fix_removes_safe_issues(tmp_path) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        _seed_store_package("ghostfix", "1.0.0", size=8)
        ghost_root = get_store_path(generate_fingerprint("ghostfix", "1.0.0"))
        import shutil

        shutil.rmtree(ghost_root)

        create_env("mlfix")
        broken_target = tmp_path / "missing_target_fix"
        broken_link = get_env_site_packages("mlfix") / "broken_pkg_fix"
        broken_link.symlink_to(broken_target)

        fixed = doctor_fix()
        assert fixed.fixed_issues >= 2
        post = doctor_check()
        assert post.ok is True
    finally:
        os.environ.pop("FORGE_HOME", None)
