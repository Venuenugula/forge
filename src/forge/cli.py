from __future__ import annotations

import argparse

from .envs import create_env
from .pip_shim import install_to_store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge")
    sub = parser.add_subparsers(dest="command", required=True)

    create_cmd = sub.add_parser("create", help="Create a Forge environment")
    create_cmd.add_argument("env", help="Environment name")
    create_cmd.add_argument("--parent", default=None, help="Parent environment")

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

    if args.command == "pip" and args.pip_command == "install":
        path = install_to_store(args.pkg, env_name=args.env)
        print(f"[pip_shim] installed {args.pkg} -> {path}")
        if args.env:
            print(f"[linker] linked into env={args.env}")
            print(f"[runtime] updated forge_layers.pth for env={args.env}")
        return 0

    parser.error("Unsupported command")
    return 1
