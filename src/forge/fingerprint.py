from __future__ import annotations

from dataclasses import dataclass, asdict
import platform
import sys
from pathlib import Path

from .config import get_store_dir


@dataclass(frozen=True)
class PackageFingerprint:
    name: str
    version: str
    python_version: str
    python_tag: str
    abi_tag: str
    platform: str
    accelerator: str = "cpu"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _python_tag() -> str:
    return f"cp{sys.version_info.major}{sys.version_info.minor}"


def generate_fingerprint(
    pkg_name: str,
    version: str,
    *,
    accelerator: str = "cpu",
) -> PackageFingerprint:
    py_tag = _python_tag()
    system = platform.system().lower()
    machine = platform.machine().lower() or "unknown"
    platform_tag = f"{system}_{machine}"

    return PackageFingerprint(
        name=pkg_name,
        version=version,
        python_version=platform.python_version(),
        python_tag=py_tag,
        abi_tag=py_tag,
        platform=platform_tag,
        accelerator=accelerator,
    )


def get_store_path(fingerprint: PackageFingerprint) -> Path:
    leaf = (
        f"{fingerprint.python_tag}-"
        f"{fingerprint.abi_tag}-"
        f"{fingerprint.platform}-"
        f"{fingerprint.accelerator}"
    )
    return (
        get_store_dir()
        / fingerprint.name
        / fingerprint.version
        / leaf
    )
