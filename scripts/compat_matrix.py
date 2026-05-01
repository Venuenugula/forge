#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run() -> int:
    parser = argparse.ArgumentParser(description="Validate Forge compatibility matrix.")
    parser.add_argument(
        "--matrix",
        default="docs/compatibility-matrix.json",
        help="Path to compatibility matrix JSON file.",
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="Fail if any declared Python minor is unavailable locally.",
    )
    args = parser.parse_args()

    matrix_path = Path(args.matrix)
    if not matrix_path.exists():
        print(f"[compat] matrix not found: {matrix_path}", file=sys.stderr)
        return 2

    payload = json.loads(matrix_path.read_text(encoding="utf-8"))
    minors: list[str] = payload.get("python_minors", [])
    checks: list[str] = payload.get("core_checks", [])
    if not minors or not checks:
        print("[compat] matrix must define python_minors and core_checks", file=sys.stderr)
        return 2

    missing: list[str] = []
    missing_deps: list[str] = []
    failed: list[str] = []
    for minor in minors:
        exe = shutil.which(f"python{minor}")
        if exe is None:
            missing.append(minor)
            print(f"[compat] python{minor} not found (skipping)")
            continue

        dep_check = subprocess.run([exe, "-c", "import pytest"], check=False, capture_output=True, text=True)
        if dep_check.returncode != 0:
            missing_deps.append(minor)
            print(f"[compat] python{minor} missing pytest (skipping)")
            continue

        cmd = [exe, "-m", "pytest", "-q", *checks]
        print(f"[compat] running {' '.join(cmd)}")
        proc = subprocess.run(cmd, check=False)
        if proc.returncode != 0:
            failed.append(minor)

    if failed:
        print(f"[compat] failed minors: {', '.join(failed)}", file=sys.stderr)
        return 1
    if args.require_all and (missing or missing_deps):
        details = []
        if missing:
            details.append(f"missing interpreters: {', '.join(missing)}")
        if missing_deps:
            details.append(f"missing pytest: {', '.join(missing_deps)}")
        print(f"[compat] {'; '.join(details)}", file=sys.stderr)
        return 1

    print("[compat] matrix validation passed")
    if missing:
        print(f"[compat] skipped minors: {', '.join(missing)}")
    if missing_deps:
        print(f"[compat] skipped minors (missing pytest): {', '.join(missing_deps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
