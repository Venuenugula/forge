from __future__ import annotations

import argparse
import json

from .envs import create_env, parent_chain
from .gc import doctor_check, doctor_fix, gc_apply, gc_dry_run
from .resolver import detect_mode, inspect_candidates, resolve_package
from .pip_shim import install_local, install_to_store_with_report, uninstall_local
from .runtime import activation_exports


def _log(message: str, *, quiet: bool = False) -> None:
    if not quiet:
        print(message)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge")
    parser.add_argument("--quiet", action="store_true", help="Minimize non-essential output")
    parser.add_argument("--verbose", action="store_true", help="Include extra diagnostic output")
    sub = parser.add_subparsers(dest="command", required=True)

    create_cmd = sub.add_parser("create", help="Create a Forge environment")
    create_cmd.add_argument("env", help="Environment name")
    create_cmd.add_argument("--parent", default=None, help="Parent environment")

    activate_cmd = sub.add_parser("activate", help="Print shell exports for an environment")
    activate_cmd.add_argument("env", help="Environment name")

    install_cmd = sub.add_parser("install", help="Install package with Forge local semantics")
    install_cmd.add_argument("pkg", help="Package spec, e.g. numpy==1.26.4")
    install_cmd.add_argument("--env", required=True, help="Target environment")
    install_cmd.add_argument("--local", action="store_true", help="Install as local override")

    uninstall_cmd = sub.add_parser("uninstall", help="Uninstall package from an environment")
    uninstall_cmd.add_argument("pkg", help="Package import name, e.g. numpy")
    uninstall_cmd.add_argument("--env", required=True, help="Target environment")
    uninstall_cmd.add_argument("--local", action="store_true", help="Uninstall local override")

    inspect_cmd = sub.add_parser("inspect", help="Inspect package resolution")
    inspect_cmd.add_argument("pkg", help="Package import name, e.g. numpy")
    inspect_cmd.add_argument("--env", required=True, help="Environment name")
    inspect_cmd.add_argument(
        "--mode",
        choices=["loose", "warn", "strict"],
        default=None,
        help="Resolution conflict mode",
    )
    inspect_cmd.add_argument("--json", action="store_true", help="Print JSON output")

    tree_cmd = sub.add_parser("tree", help="Show env parent chain")
    tree_cmd.add_argument("env", help="Environment name")

    gc_cmd = sub.add_parser("gc", help="Garbage collection")
    gc_cmd.add_argument("--dry-run", action="store_true", help="Preview reclaimable packages")
    gc_cmd.add_argument("--force", action="store_true", help="Apply deletion of unused packages")
    gc_cmd.add_argument("--json", action="store_true", help="Print JSON output")

    doctor_cmd = sub.add_parser("doctor", help="Check metadata/filesystem consistency")
    doctor_cmd.add_argument("--fix", action="store_true", help="Attempt to auto-fix safe issues")
    doctor_cmd.add_argument("--json", action="store_true", help="Print JSON output")

    pip_cmd = sub.add_parser("pip", help="Store-first pip wrapper")
    pip_sub = pip_cmd.add_subparsers(dest="pip_command", required=True)
    pip_install = pip_sub.add_parser("install", help="Install package to Forge store")
    pip_install.add_argument("pkg", help="Package spec, e.g. numpy==1.26.4")
    pip_install.add_argument("--env", default=None, help="Link package into environment")
    pip_install.add_argument(
        "--abi-policy",
        choices=["strict_abi", "warn_abi", "allow_abi"],
        default="warn_abi",
        help="Control ABI-compatible reuse policy",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "create":
        create_env(args.env, parent=args.parent)
        _log(f"[envs] created env={args.env} parent={args.parent}", quiet=args.quiet)
        return 0

    if args.command == "activate":
        _log(activation_exports(args.env), quiet=False)
        return 0

    if args.command == "install":
        if not args.local:
            parser.error("MVP supports only --local for forge install")
        path = install_local(args.pkg, env_name=args.env)
        _log(f"[install] local package={args.pkg} env={args.env} path={path}", quiet=args.quiet)
        return 0

    if args.command == "uninstall":
        if not args.local:
            parser.error("MVP supports only --local for forge uninstall")
        path = uninstall_local(args.pkg, env_name=args.env)
        _log(f"[uninstall] local package={args.pkg} env={args.env} path={path}", quiet=args.quiet)
        return 0

    if args.command == "inspect":
        candidates = inspect_candidates(args.pkg, args.env)
        result = resolve_package(args.pkg, args.env, mode=args.mode or detect_mode())
        if args.json:
            payload = {
                "package": args.pkg,
                "resolution": result.to_dict(),
                "candidates": candidates.to_dict(),
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0

        _log(f"[inspect] package={args.pkg} source={result.source} version={result.version}", quiet=args.quiet)
        local = candidates.local
        _log(f"[candidate:local] exists={local.exists} version={local.version} path={local.path}", quiet=args.quiet)
        for parent in candidates.parents:
            _log(
                f"[candidate:parent:{parent.env}] exists={parent.exists} "
                f"version={parent.version} path={parent.path}",
                quiet=args.quiet,
            )
        _log(f"[candidate:global] versions={candidates.global_versions}", quiet=args.quiet)
        if result.reason:
            _log(f"[explain] {result.reason}", quiet=args.quiet)
        if result.shadowed_sources:
            _log(f"[shadowed] {', '.join(result.shadowed_sources)}", quiet=args.quiet)
        for warning in result.warnings:
            _log(f"[warn] {warning}", quiet=args.quiet)
        return 0

    if args.command == "tree":
        chain = [args.env, *parent_chain(args.env)]
        _log("[tree] " + " -> ".join(chain), quiet=args.quiet)
        return 0

    if args.command == "gc":
        if not args.dry_run and not args.force:
            parser.error("Use either --dry-run or --force")
        result = gc_apply(force=True) if args.force else gc_dry_run()
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
            return 0
        if args.force:
            _log("Deleted:", quiet=args.quiet)
        else:
            _log("Unused:", quiet=args.quiet)
        for row in result.unused:
            mib = row.size_bytes / (1024 * 1024)
            _log(f"- {row.name} {row.version} ({mib:.2f} MiB)", quiet=args.quiet)
        total_mib = result.reclaimable_bytes / (1024 * 1024)
        label = "Total reclaimed" if args.force else "Total reclaimable"
        _log(f"{label}: {total_mib:.2f} MiB", quiet=args.quiet)
        return 0

    if args.command == "doctor":
        report = doctor_fix() if args.fix else doctor_check()
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
            return 0
        if report.ok:
            _log("Doctor check: OK", quiet=args.quiet)
            _log(
                f"Scanned metadata={report.metadata_rows_scanned} "
                f"envs={report.envs_scanned} symlinks={report.symlinks_scanned}",
                quiet=args.quiet,
            )
            return 0
        _log("Doctor check: issues found", quiet=args.quiet)
        for issue in report.issues:
            _log(f"- [{issue.kind}] {issue.path} :: {issue.detail}", quiet=args.quiet)
        _log(
            f"Scanned metadata={report.metadata_rows_scanned} "
            f"envs={report.envs_scanned} symlinks={report.symlinks_scanned}",
            quiet=args.quiet,
        )
        if report.fixed_issues:
            _log(f"Fixed issues: {report.fixed_issues}", quiet=args.quiet)
        return 0

    if args.command == "pip" and args.pip_command == "install":
        report = install_to_store_with_report(args.pkg, env_name=args.env, abi_policy=args.abi_policy)
        _log(f"[pip_shim] installed {args.pkg} -> {report.path}", quiet=args.quiet)
        _log(f"[reuse] reused={report.reused} kind={report.reuse_kind}", quiet=args.quiet)
        if args.verbose:
            _log(f"[abi_policy] {args.abi_policy}", quiet=args.quiet)
        for warning in report.warnings:
            _log(f"[warn] {warning}", quiet=args.quiet)
        if args.env:
            _log(f"[linker] linked into env={args.env}", quiet=args.quiet)
            _log(f"[runtime] updated forge_layers.pth for env={args.env}", quiet=args.quiet)
        return 0

    parser.error("Unsupported command")
    return 1
