from __future__ import annotations

import io
import os
import platform
import sys
from contextlib import redirect_stdout

from forge.cli import main
from forge.envs import create_env, load_env_config


def test_cli_inspect_prints_candidates(tmp_path, monkeypatch) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("base")
        create_env("child", parent="base")

        monkeypatch.setattr(
            "forge.cli.inspect_candidates",
            lambda pkg, env: {
                "local": {"exists": False, "version": None, "path": "/tmp/local"},
                "parents": [{"env": "base", "exists": True, "version": "1.26.4", "path": "/tmp/base"}],
                "global_versions": ["1.26.4"],
            },
        )
        monkeypatch.setattr(
            "forge.cli.resolve_package",
            lambda pkg, env, mode=None: {"source": "parent:base", "version": "1.26.4", "warnings": []},
        )

        monkeypatch.setattr(sys, "argv", ["forge", "inspect", "numpy", "--env", "child", "--mode", "warn"])
        out = io.StringIO()
        with redirect_stdout(out):
            code = main()
        text = out.getvalue()
        assert code == 0
        assert "[candidate:local]" in text
        assert "[candidate:parent:base]" in text
        assert "[candidate:global]" in text
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_cli_activate_prints_layered_exports(tmp_path, monkeypatch) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("base")
        create_env("child", parent="base")
        monkeypatch.setattr(sys, "argv", ["forge", "activate", "child"])
        out = io.StringIO()
        with redirect_stdout(out):
            code = main()
        text = out.getvalue()
        assert code == 0
        assert "export FORGE_ACTIVE_ENV=child" in text
        assert "/envs/child/site-packages" in text
        assert "/envs/base/site-packages" in text
        assert "/store" in text
        assert "PYTHONPATH" in text
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_create_env_defaults_python_version(tmp_path) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("pyenv")
        cfg = load_env_config("pyenv")
        assert cfg["python_version"] == platform.python_version()
    finally:
        os.environ.pop("FORGE_HOME", None)
