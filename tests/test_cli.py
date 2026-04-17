from __future__ import annotations

import io
import os
import platform
import sys
import json
from contextlib import redirect_stdout

from forge.cli import main
from forge.envs import create_env, load_env_config
from forge.models import CandidateEntry, DoctorIssue, DoctorReport, InspectCandidates, ResolveResult, GCReport


def test_cli_inspect_prints_candidates(tmp_path, monkeypatch) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("base")
        create_env("child", parent="base")

        monkeypatch.setattr(
            "forge.cli.inspect_candidates",
            lambda pkg, env: InspectCandidates(
                local=CandidateEntry(exists=False, version=None, path="/tmp/local"),
                parents=[CandidateEntry(env="base", exists=True, version="1.26.4", path="/tmp/base")],
                global_versions=["1.26.4"],
            ),
        )
        monkeypatch.setattr(
            "forge.cli.resolve_package",
            lambda pkg, env, mode=None: ResolveResult(source="parent:base", version="1.26.4", warnings=[]),
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


def test_cli_inspect_json_output(tmp_path, monkeypatch) -> None:
    os.environ["FORGE_HOME"] = str(tmp_path / ".forge")
    try:
        create_env("base")
        create_env("child", parent="base")
        monkeypatch.setattr(
            "forge.cli.inspect_candidates",
            lambda pkg, env: InspectCandidates(
                local=CandidateEntry(exists=False, version=None, path="/tmp/local"),
                parents=[CandidateEntry(env="base", exists=True, version="1.26.4", path="/tmp/base")],
                global_versions=["1.26.4"],
            ),
        )
        monkeypatch.setattr(
            "forge.cli.resolve_package",
            lambda pkg, env, mode=None: ResolveResult(source="parent:base", version="1.26.4", warnings=[]),
        )
        monkeypatch.setattr(
            sys, "argv", ["forge", "inspect", "numpy", "--env", "child", "--mode", "warn", "--json"]
        )
        out = io.StringIO()
        with redirect_stdout(out):
            code = main()
        payload = json.loads(out.getvalue())
        assert code == 0
        assert payload["package"] == "numpy"
        assert payload["resolution"]["source"] == "parent:base"
        assert payload["candidates"]["parents"][0]["env"] == "base"
    finally:
        os.environ.pop("FORGE_HOME", None)


def test_cli_gc_json_output(monkeypatch) -> None:
    monkeypatch.setattr(
        "forge.cli.gc_dry_run",
        lambda: GCReport(unused=[], reclaimable_bytes=0),
    )
    monkeypatch.setattr(sys, "argv", ["forge", "gc", "--dry-run", "--json"])
    out = io.StringIO()
    with redirect_stdout(out):
        code = main()
    payload = json.loads(out.getvalue())
    assert code == 0
    assert payload["reclaimable_bytes"] == 0
    assert payload["unused"] == []


def test_cli_doctor_json_output(monkeypatch) -> None:
    monkeypatch.setattr(
        "forge.cli.doctor_check",
        lambda: DoctorReport(ok=False, issues=[DoctorIssue(kind="broken_symlink", path="/tmp/x", detail="bad")]),
    )
    monkeypatch.setattr(sys, "argv", ["forge", "doctor", "--json"])
    out = io.StringIO()
    with redirect_stdout(out):
        code = main()
    payload = json.loads(out.getvalue())
    assert code == 0
    assert payload["ok"] is False
    assert payload["issues"][0]["kind"] == "broken_symlink"


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
