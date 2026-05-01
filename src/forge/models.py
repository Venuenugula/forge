from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CandidateEntry:
    exists: bool
    version: str | None
    path: str
    env: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class InspectCandidates:
    local: CandidateEntry
    parents: list[CandidateEntry]
    global_versions: list[str]

    def to_dict(self) -> dict:
        return {
            "local": self.local.to_dict(),
            "parents": [p.to_dict() for p in self.parents],
            "global_versions": list(self.global_versions),
        }


@dataclass(frozen=True)
class ResolveResult:
    source: str
    version: str | None
    warnings: list[str]
    reason: str | None = None
    shadowed_sources: list[str] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GCUnusedEntry:
    name: str
    version: str
    path: str
    size_bytes: int
    ref_count: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GCReport:
    unused: list[GCUnusedEntry]
    reclaimable_bytes: int

    def to_dict(self) -> dict:
        return {
            "unused": [item.to_dict() for item in self.unused],
            "reclaimable_bytes": self.reclaimable_bytes,
        }


@dataclass(frozen=True)
class DoctorIssue:
    kind: str
    path: str
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DoctorReport:
    ok: bool
    issues: list[DoctorIssue]
    metadata_rows_scanned: int = 0
    envs_scanned: int = 0
    symlinks_scanned: int = 0

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "issues": [i.to_dict() for i in self.issues],
            "metadata_rows_scanned": self.metadata_rows_scanned,
            "envs_scanned": self.envs_scanned,
            "symlinks_scanned": self.symlinks_scanned,
        }


@dataclass(frozen=True)
class InstallReport:
    path: str
    reused: bool
    reuse_kind: str
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)
