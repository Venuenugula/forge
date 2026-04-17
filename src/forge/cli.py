from __future__ import annotations

import argparse

from .envs import create_env, parent_chain
from .gc import gc_dry_run
from .resolver import detect_mode, resolve_package
from .pip_shim import install_to_store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge")
    sub = parser.add_subparsers(dest="command", required=True)

    create_cmd = sub.add_parser("create", help="Create a Forge environment")
    create_cmd.add_argument("env", help="Environment name")
    create_cmd.add_argument("--parent", default=None, help="Parent environment")

    inspect_cmd = sub.add_parser("inspect", help="Inspect package resolution")
    inspect_cmd.add_argument("pkg", help="Package import name, e.g. numpy")
    inspect_cmd.add_argument("--env", required=True, help="Environment name")
    inspect_cmd.add_argument(
        "--mode",
        choices=["loose", "warn", "strict"],
        default=None,
        help="Resolution conflict mode",
    )

    tree_cmd = sub.add_parser("tree", help="Show env parent chain")
    tree_cmd.add_argument("env", help="Environment name")

    gc_cmd = sub.add_parser("gc", help="Garbage collection")
    gc_cmd.add_argument("--dry-run", action="store_true", help="Preview reclaimable packages")

    pip_cmd = sub.add_parser("pip", help="Store-first pip wrapper")
    pip_sub = pip_cmd.add_subparsers(dest="pip_command", required=True)
    pip_install = pip_sub.add_parser("install", help="Install package to Forge store")
    pip_install.add_argument("pkg", help="Package spec, e.g. numpy==1.26.4")
    pip_install.add_argument("--env", default=None, help="Link package into environment")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "create":
        create_env(args.env, parent=args.parent)
        print(f"[envs] created env={args.env} parent={args.parent}")
        return 0

    if args.command == "inspect":
        result = resolve_package(args.pkg, args.env, mode=args.mode or detect_mode())
        print(f"[inspect] package={args.pkg} source={result['source']} version={result['version']}")
        for warning in result["warnings"]:
            print(f"[warn] {warning}")
        return 0

    if args.command == "tree":
        chain = [args.env, *parent_chain(args.env)]
        print("[tree] " + " -> ".join(chain))
        return 0

    if args.command == "gc":
        if not args.dry_run:
            parser.error("Only --dry-run is supported in MVP")
        result = gc_dry_run()
        print("Unused:")
        for row in result["unused"]:
            mib = row["size_bytes"] / (1024 * 1024)
            print(f"- {row['name']} {row['version']} ({mib:.2f} MiB)")
        total_mib = result["reclaimable_bytes"] / (1024 * 1024)
        print(f"Total reclaimable: {total_mib:.2f} MiB")
        return 0

    if args.command == "pip" and args.pip_command == "install":
        path = install_to_store(args.pkg, env_name=args.env)
        print(f"[pip_shim] installed {args.pkg} -> {path}")
        if args.env:
            print(f"[linker] linked into env={args.env}")
            print(f"[runtime] updated forge_layers.pth for env={args.env}")
        return 0

    parser.error("Unsupported command")
    return 1
