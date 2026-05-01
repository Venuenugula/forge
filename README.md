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

### Day 10 (Current Slice)
- Added exact store package reuse in `forge pip install` path to skip redundant reinstalls.
- Added test coverage verifying second identical install reuses cached store content.

## Next Milestones

- Add ABI-compatible reuse policy and warnings (`reuse + warn`) instead of exact-only behavior.
- Add `inspect` output for shadowing rationale (why selected layer won).
- Harden GC/doctor with optional auto-fix suggestions and richer summary stats.
