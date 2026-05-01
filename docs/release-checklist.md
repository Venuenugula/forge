# Forge Release Checklist

Use this checklist for every Forge release.

## 1) Pre-Release Validation

- [ ] Working tree is clean.
- [ ] `pytest -q` passes locally.
- [ ] `bash scripts/smoke.sh` passes locally.
- [ ] No high-severity open bugs for release scope.

## 2) Version and Packaging

- [ ] Update version in `pyproject.toml`.
- [ ] Build artifacts:
  - [ ] `python -m pip install build`
  - [ ] `python -m build`
- [ ] Verify `dist/` contains both sdist and wheel.

## 3) Release Notes

- [ ] Copy `docs/release-notes-template.md` into release draft.
- [ ] Fill Highlights, Breaking Changes, Upgrade Notes, and Verification.
- [ ] Include commit range and notable fixes.

## 4) Tag and Publish

- [ ] Commit version/release-doc updates.
- [ ] Create annotated tag (example: `v0.1.1`).
- [ ] Push branch and tag to remote.
- [ ] Create GitHub release from the tag.

## 5) Post-Release Checks

- [ ] Confirm release assets are downloadable.
- [ ] Re-run smoke test against released package if applicable.
- [ ] Open follow-up issues for deferred items.
