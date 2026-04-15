from __future__ import annotations

import os

from forge.config import ensure_dirs, get_db_path, get_store_dir
from forge.fingerprint import generate_fingerprint, get_store_path
from forge.metadata import (
    decrement_ref_count,
    get_connection,
    get_package,
    increment_ref_count,
    init_db,
    list_packages,
    register_package,
)


def test_fingerprint_and_store_path_are_deterministic(tmp_path) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        ensure_dirs()
        fp1 = generate_fingerprint("numpy", "1.26.4")
        fp2 = generate_fingerprint("numpy", "1.26.4")

        assert fp1 == fp2

        store_path = get_store_path(fp1)
        assert str(store_path).startswith(str(get_store_dir()))
        assert store_path.parts[-3] == "numpy"
        assert store_path.parts[-2] == "1.26.4"
        assert fp1.python_tag in store_path.parts[-1]
        assert fp1.platform in store_path.parts[-1]
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_metadata_register_dedup_and_refcount_lifecycle(tmp_path) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        ensure_dirs()
        conn = get_connection()
        init_db(conn)

        fp = generate_fingerprint("torch", "2.2.0")
        path = get_store_path(fp)

        register_package(conn, fp, path)
        register_package(conn, fp, path)
        rows = list_packages(conn)
        assert len(rows) == 1

        row = get_package(conn, fp)
        assert row is not None
        assert row["ref_count"] == 0
        assert row["path"] == str(path)

        increment_ref_count(conn, path)
        increment_ref_count(conn, path)
        row = get_package(conn, fp)
        assert row is not None
        assert row["ref_count"] == 2

        decrement_ref_count(conn, path)
        decrement_ref_count(conn, path)
        decrement_ref_count(conn, path)
        row = get_package(conn, fp)
        assert row is not None
        assert row["ref_count"] == 0

        assert get_db_path().exists()
        conn.close()
    finally:
        os.environ.pop("FORGE_HOME", None)
