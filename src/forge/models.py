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
