from __future__ import annotations

import os
from pathlib import Path

from forge.config import ensure_dirs, get_db_path, get_store_dir
from forge.envs import create_env, get_env_site_packages, load_env_config, save_env_config
from forge.fingerprint import PackageFingerprint, generate_fingerprint, get_store_path
from forge.metadata import (
    decrement_ref_count,
    get_connection,
    get_package,
    increment_ref_count,
    init_db,
    list_packages,
    register_package,
)
from forge.pip_shim import install_local, install_to_store, install_to_store_with_report, uninstall_local


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


def test_install_to_store_and_link_into_env_updates_metadata(tmp_path, monkeypatch) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("ml_base")

        class DummyCompleted:
            def __init__(self) -> None:
                self.returncode = 0
                self.stdout = "ok"
                self.stderr = ""

        def fake_run(cmd, check, capture_output, text):  # noqa: ANN001
            target = Path(cmd[-1])
            (target / "numpy").mkdir(parents=True, exist_ok=True)
            (target / "numpy" / "__init__.py").write_text("__version__='1.26.4'\n", encoding="utf-8")
            (target / "numpy-1.26.4.dist-info").mkdir(parents=True, exist_ok=True)
            return DummyCompleted()

        monkeypatch.setattr("forge.pip_shim.subprocess.run", fake_run)

        store_path = install_to_store("numpy==1.26.4", env_name="ml_base")
        env_site = get_env_site_packages("ml_base")

        assert (store_path / "numpy").exists()
        assert (env_site / "numpy").is_symlink()

        pth_path = env_site / "forge_layers.pth"
        assert pth_path.exists()
        pth = pth_path.read_text(encoding="utf-8")
        assert str(env_site) in pth
        assert str(get_store_dir()) in pth

        conn = get_connection()
        init_db(conn)
        fp = generate_fingerprint("numpy", "1.26.4")
        row = get_package(conn, fp)
        assert row is not None
        assert row["ref_count"] == 1
        conn.close()
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_install_local_updates_env_manifest(tmp_path, monkeypatch) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("ml_local")

        class DummyCompleted:
            def __init__(self) -> None:
                self.returncode = 0
                self.stdout = "ok"
                self.stderr = ""

        def fake_run(cmd, check, capture_output, text):  # noqa: ANN001
            target = Path(cmd[-1])
            (target / "numpy").mkdir(parents=True, exist_ok=True)
            (target / "numpy" / "__init__.py").write_text("__version__='1.25.0'\n", encoding="utf-8")
            (target / "numpy-1.25.0.dist-info").mkdir(parents=True, exist_ok=True)
            return DummyCompleted()

        monkeypatch.setattr("forge.pip_shim.subprocess.run", fake_run)

        path = install_local("numpy==1.25.0", "ml_local")
        assert path.exists()

        cfg = load_env_config("ml_local")
        assert cfg["packages"]["numpy"] == "1.25.0"
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_install_to_store_raises_on_python_version_mismatch(tmp_path, monkeypatch) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("mismatch")
        cfg = load_env_config("mismatch")
        cfg["python_version"] = "3.11.0"
        save_env_config("mismatch", cfg)

        class DummyCompleted:
            def __init__(self) -> None:
                self.returncode = 0
                self.stdout = "ok"
                self.stderr = ""

        def fake_run(cmd, check, capture_output, text):  # noqa: ANN001
            target = Path(cmd[-1])
            (target / "numpy").mkdir(parents=True, exist_ok=True)
            return DummyCompleted()

        monkeypatch.setattr("forge.pip_shim.subprocess.run", fake_run)

        raised = False
        try:
            install_to_store("numpy==1.26.4", env_name="mismatch")
        except RuntimeError as exc:
            raised = True
            assert "Python version mismatch" in str(exc)
        assert raised
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_uninstall_local_removes_manifest_symlink_and_decrements_refcount(tmp_path, monkeypatch) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("ml_uninstall")

        class DummyCompleted:
            def __init__(self) -> None:
                self.returncode = 0
                self.stdout = "ok"
                self.stderr = ""

        def fake_run(cmd, check, capture_output, text):  # noqa: ANN001
            target = Path(cmd[-1])
            (target / "numpy").mkdir(parents=True, exist_ok=True)
            (target / "numpy" / "__init__.py").write_text("__version__='1.26.4'\n", encoding="utf-8")
            (target / "numpy-1.26.4.dist-info").mkdir(parents=True, exist_ok=True)
            return DummyCompleted()

        monkeypatch.setattr("forge.pip_shim.subprocess.run", fake_run)

        store_path = install_local("numpy==1.26.4", "ml_uninstall")
        cfg = load_env_config("ml_uninstall")
        assert cfg["packages"]["numpy"] == "1.26.4"

        env_site = get_env_site_packages("ml_uninstall")
        assert (env_site / "numpy").is_symlink()

        removed_path = uninstall_local("numpy", "ml_uninstall")
        assert removed_path == store_path

        cfg = load_env_config("ml_uninstall")
        assert "numpy" not in cfg["packages"]
        assert not (env_site / "numpy").exists()

        conn = get_connection()
        try:
            init_db(conn)
            fp = generate_fingerprint("numpy", "1.26.4")
            row = get_package(conn, fp)
            assert row is not None
            assert row["ref_count"] == 0
        finally:
            conn.close()
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_install_to_store_reuses_existing_exact_store_package(tmp_path, monkeypatch) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        calls = {"count": 0}

        class DummyCompleted:
            def __init__(self) -> None:
                self.returncode = 0
                self.stdout = "ok"
                self.stderr = ""

        def fake_run(cmd, check, capture_output, text):  # noqa: ANN001
            calls["count"] += 1
            target = Path(cmd[-1])
            (target / "numpy").mkdir(parents=True, exist_ok=True)
            (target / "numpy" / "__init__.py").write_text("__version__='1.26.4'\n", encoding="utf-8")
            (target / "numpy-1.26.4.dist-info").mkdir(parents=True, exist_ok=True)
            return DummyCompleted()

        monkeypatch.setattr("forge.pip_shim.subprocess.run", fake_run)

        first = install_to_store("numpy==1.26.4")
        second = install_to_store("numpy==1.26.4")

        assert first == second
        assert calls["count"] == 1
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_install_to_store_with_report_respects_abi_policy(tmp_path, monkeypatch) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        calls = {"count": 0}

        class DummyCompleted:
            def __init__(self) -> None:
                self.returncode = 0
                self.stdout = "ok"
                self.stderr = ""

        def fake_run(cmd, check, capture_output, text):  # noqa: ANN001
            calls["count"] += 1
            target = Path(cmd[-1])
            (target / "numpy").mkdir(parents=True, exist_ok=True)
            (target / "numpy" / "__init__.py").write_text("__version__='1.26.4'\n", encoding="utf-8")
            (target / "numpy-1.26.4.dist-info").mkdir(parents=True, exist_ok=True)
            return DummyCompleted()

        monkeypatch.setattr("forge.pip_shim.subprocess.run", fake_run)

        fp = generate_fingerprint("numpy", "1.26.4")
        compatible_fp = PackageFingerprint(
            name=fp.name,
            version=fp.version,
            python_version="0.0.0",
            python_tag=fp.python_tag,
            abi_tag=fp.abi_tag,
            platform=fp.platform,
            accelerator=fp.accelerator,
        )
        compatible_path = get_store_path(compatible_fp)
        compatible_path.mkdir(parents=True, exist_ok=True)
        (compatible_path / "numpy").mkdir(parents=True, exist_ok=True)
        (compatible_path / "numpy" / "__init__.py").write_text("__version__='1.26.4'\n", encoding="utf-8")

        conn = get_connection()
        try:
            init_db(conn)
            register_package(conn, compatible_fp, compatible_path)
        finally:
            conn.close()

        warn_report = install_to_store_with_report("numpy==1.26.4", abi_policy="warn_abi")
        strict_report = install_to_store_with_report("numpy==1.26.4", abi_policy="strict_abi")

        assert warn_report.reused is True
        assert warn_report.reuse_kind == "abi_compatible"
        assert strict_report.reuse_kind in {"fresh", "exact"}
        assert calls["count"] == 1
    finally:
        os.environ.pop("FORGE_HOME", None)
