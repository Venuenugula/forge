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

## Day 1 Deliverables

- project scaffold created
- baseline package/test files created
- README with scope, architecture intent, and delivery workflow

## Next Immediate Target (Day 2)

Implement:
- `src/forge/config.py`
- `src/forge/fingerprint.py`
- `src/forge/metadata.py`

Goal for Day 2:
- initialize `~/.forge` directories
- create SQLite schema
- compute deterministic store path fingerprints
