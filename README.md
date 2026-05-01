# Forge

Forge is a layered dependency runtime for Python.

## Mission

Forge solves:
- dependency duplication across environments
- environment explosion
- CUDA/ABI mismatch risk

Forge delivers:
- shared immutable package store
- layered environments (`LOCAL > PARENT > GLOBAL`)
- local override with safety modes
- zero duplication in the common case

## MVP Scope (Locked v1.1)

Build:
- global package store
- SQLite metadata
- `forge pip` shim
- environment creation
- symlink linking (Linux/macOS first)
- `.pth` injection runtime
- resolver and basic GC

Do not build:
- Docker export
- UI
- cloud sync

## Repository Structure

```text
forge/
  pyproject.toml
  README.md
  src/forge/
    __init__.py
    cli.py
    config.py
    models.py
    metadata.py
    fingerprint.py
    envs.py
    resolver.py
    pip_shim.py
    linker.py
    runtime.py
    gc.py
    utils.py
  tests/
    test_resolver.py
    test_store_reuse.py
    test_gc.py
```

## Day-by-Day Working Agreement

- One feature slice at a time.
- Audit each file/feature before moving forward.
- Commit in small, reviewable units.
- Push to GitHub only when explicitly requested.

## Build Log

### Day 1
- Scaffolded project structure and packaging entrypoint.
- Added baseline README and delivery workflow.

### Day 2
- Implemented Forge path config, fingerprint generation, and SQLite metadata layer.
- Added first tests for deterministic store identity and refcount lifecycle.

### Day 3
- Implemented env creation, linker, `.pth` runtime layering, and pip shim integration.
- Added end-to-end install/link tests.

### Day 4
- Implemented resolver conflict modes (`loose`, `warn`, `strict`), `inspect`, `tree`, and GC dry-run command.
- Added resolver and GC validation tests.

### Day 5
- Added `forge install ... --local` flow and env manifest recording.
- Improved `inspect` output to show local/parent/global candidates.

### Day 6
- Added `forge activate <env>` with deterministic layered `PYTHONPATH` export output.
- Added env Python version defaulting and install-time compatibility checks.

### Day 7
- Introduced typed models for inspect/gc output.
- Added `--json` output support for `inspect` and `gc`.
- Added `.gitignore` entries for Python cache artifacts.

### Day 8
- Added `gc --force` destructive cleanup path.
- Added `doctor` consistency checks for metadata/filesystem drift and broken symlinks.

### Day 9
- Added `forge uninstall <pkg> --env <env> --local`.
- Implemented symlink cleanup + manifest cleanup + ref_count decrement behavior.

### Day 10
- Added exact store package reuse in `forge pip install` path to skip redundant reinstalls.
- Added test coverage verifying second identical install reuses cached store content.

### Day 11
- Added installer reuse reporting (`reused`, `reuse_kind`, warnings) and CLI visibility.
- Added ABI-compatible reuse fallback logic in installer metadata lookup path.

### Day 12
- Added resolver explainability fields (`reason`, `shadowed_sources`) for inspect output.
- Enhanced human-readable inspect output with resolution rationale.

### Day 13
- Added doctor summary counters (`metadata_rows_scanned`, `envs_scanned`, `symlinks_scanned`).
- Enhanced doctor CLI output with scan summary metrics.

### Day 14
- Added explicit ABI policy handling on pip shim install path: `strict_abi`, `warn_abi`, `allow_abi`.
- Kept reuse reporting structured via install report fields.

### Day 15
- Added CLI global output controls: `--quiet` and `--verbose`.
- Exposed pip install ABI policy selection through CLI (`forge pip install --abi-policy`).

### Day 16
- Added `doctor --fix` safe auto-remediation for broken symlinks and stale metadata rows.
- Extended doctor report model with `fixed_issues` for before/after remediation visibility.

### Day 17
- Added per-environment default settings in `config.json`, including default `abi_policy`.
- Installer now resolves ABI policy from env settings when an environment is targeted.

### Day 18
- Added CI-oriented enforcement mode (`--enforce`) for non-zero exits on policy violations.
- Added command-specific enforcement exit codes for pip warnings and doctor issues.

### Day 19
- Added `forge env set` and `forge env get` commands to manage per-environment settings.
- Added JSON-capable output for environment settings retrieval for automation.

### Day 20
- Added `forge doctor --fix --dry-run` planning mode to preview safe fixes before mutation.
- Kept doctor fix reporting structured with planned/applied fix counts.

### Day 21
- Added CI enforcement profile control via `--enforce-profile {warn,strict}`.
- Added strict-mode inspect enforcement for dependency shadowing risk signals.

### Day 22
- Extended test coverage for env settings CLI paths and strict inspect enforcement behavior.
- Added regression coverage for doctor dry-run preview semantics.

### Day 23
- Wired env-configured ABI policy into install behavior validation to ensure policy compliance.
- Added test coverage proving env-level ABI policy affects pip shim install decisions.

### Day 24
- Completed MVP production hardening pass across CLI policy controls, doctor workflows, and env settings UX.
- Refreshed operational documentation with newly available policy and safety controls.

## Next Milestones

- Add release packaging workflow (wheel build + version/tag checklist).
- Add smoke test script for end-to-end CLI flows (`create/install/activate/inspect/doctor/gc`).
- Add installation and migration guide for first-time Forge users.
