from __future__ import annotations

from pathlib import Path
import shutil

from .config import get_store_dir
from .envs import get_env_site_packages, list_env_names
from .metadata import get_connection, init_db, list_packages
from .models import DoctorIssue, DoctorReport, GCReport, GCUnusedEntry


def _dir_size_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def _used_store_roots() -> set[Path]:
    used: set[Path] = set()
    for env_name in list_env_names():
        site = get_env_site_packages(env_name)
        if not site.exists():
            continue
        for item in site.iterdir():
            if not item.is_symlink():
                continue
            resolved = item.resolve()
            # /.../store/<name>/<version>/<leaf>/<module_or_dist_info>
            root = resolved.parent
            if get_store_dir().resolve() in root.parents:
                used.add(root)
    return used


def gc_dry_run() -> GCReport:
    conn = get_connection()
    try:
        init_db(conn)
        rows = list_packages(conn)
    finally:
        conn.close()

    used_roots = _used_store_roots()
    unused: list[GCUnusedEntry] = []
    reclaimable = 0
    for row in rows:
        path = Path(row["path"])
        if path in used_roots:
            continue
        size = _dir_size_bytes(path)
        reclaimable += size
        unused.append(
            GCUnusedEntry(
                name=row["name"],
                version=row["version"],
                path=str(path),
                size_bytes=size,
                ref_count=row["ref_count"],
            )
        )

    return GCReport(unused=unused, reclaimable_bytes=reclaimable)


def gc_apply(force: bool = False) -> GCReport:
    report = gc_dry_run()
    if not force:
        raise RuntimeError("Refusing destructive GC without force=True")

    conn = get_connection()
    try:
        init_db(conn)
        for row in report.unused:
            path = Path(row.path)
            if path.exists():
                shutil.rmtree(path)
            conn.execute("DELETE FROM packages WHERE path = ?", (row.path,))
        conn.commit()
    finally:
        conn.close()
    return report


def doctor_check() -> DoctorReport:
    issues: list[DoctorIssue] = []
    metadata_rows_scanned = 0
    envs_scanned = 0
    symlinks_scanned = 0

    conn = get_connection()
    try:
        init_db(conn)
        rows = list_packages(conn)
    finally:
        conn.close()

    for row in rows:
        metadata_rows_scanned += 1
        pkg_path = Path(row["path"])
        if not pkg_path.exists():
            issues.append(
                DoctorIssue(
                    kind="metadata_missing_path",
                    path=str(pkg_path),
                    detail=f"Metadata exists for {row['name']} {row['version']} but path is missing",
                )
            )

    for env_name in list_env_names():
        envs_scanned += 1
        site = get_env_site_packages(env_name)
        if not site.exists():
            continue
        for entry in site.iterdir():
            symlinks_scanned += 1
            if entry.is_symlink() and not entry.resolve().exists():
                issues.append(
                    DoctorIssue(
                        kind="broken_symlink",
                        path=str(entry),
                        detail=f"Broken symlink in env '{env_name}'",
                    )
                )

    return DoctorReport(
        ok=len(issues) == 0,
        issues=issues,
        metadata_rows_scanned=metadata_rows_scanned,
        envs_scanned=envs_scanned,
        symlinks_scanned=symlinks_scanned,
    )
