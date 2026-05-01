#!/usr/bin/env bash
set -euo pipefail

# Forge end-to-end smoke script.
# Optional online install path can be enabled with:
#   FORGE_SMOKE_PKG="numpy==1.26.4" bash scripts/smoke.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
export FORGE_HOME="${TMP_DIR}/.forge"
export PYTHONPATH="${ROOT_DIR}/src"

cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

run_forge() {
  python -m forge.cli "$@"
}

echo "[smoke] FORGE_HOME=${FORGE_HOME}"
echo "[smoke] create base/app envs"
run_forge create base
run_forge create app --parent base

echo "[smoke] env settings"
run_forge env set app abi_policy warn_abi
run_forge env get app --json >/dev/null

echo "[smoke] activate and tree"
run_forge activate app >/dev/null
run_forge tree app >/dev/null

echo "[smoke] inspect + doctor + gc"
run_forge inspect pip --env app --mode warn >/dev/null
run_forge doctor >/dev/null
run_forge doctor --fix --dry-run >/dev/null
run_forge gc --dry-run >/dev/null

if [[ "${FORGE_SMOKE_PKG:-}" != "" ]]; then
  echo "[smoke] optional install path with ${FORGE_SMOKE_PKG}"
  run_forge pip install "${FORGE_SMOKE_PKG}" --env app --abi-policy warn_abi >/dev/null
  PKG_NAME="${FORGE_SMOKE_PKG%%==*}"
  run_forge inspect "${PKG_NAME}" --env app --mode warn >/dev/null
  run_forge uninstall "${PKG_NAME}" --env app --local >/dev/null || true
fi

echo "[smoke] success"
