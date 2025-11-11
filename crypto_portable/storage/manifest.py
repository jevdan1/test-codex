"""Manifest helpers."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class ManifestEntry:
    date: date
    rows: int
    first_ms: int
    last_ms: int
    complete: bool
    part_until: Optional[str]
    gaps: List[Dict[str, int]] = field(default_factory=list)
    checksum: Optional[str] = None

    @property
    def state(self) -> str:
        return "complete" if self.complete else "partial"


@dataclass(slots=True)
class Manifest:
    pair: str
    granularity: str
    entries: Dict[str, ManifestEntry] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair": self.pair,
            "granularity": self.granularity,
            "entries": {
                key: {
                    "date": key,
                    "rows": entry.rows,
                    "first_ms": entry.first_ms,
                    "last_ms": entry.last_ms,
                    "complete": entry.complete,
                    "part_until": entry.part_until,
                    "gaps": entry.gaps,
                    **({"checksum": entry.checksum} if entry.checksum else {}),
                }
                for key, entry in self.entries.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Manifest":
        manifest = cls(pair=data.get("pair", ""), granularity=data.get("granularity", ""))
        for key, entry in (data.get("entries") or {}).items():
            manifest.entries[key] = ManifestEntry(
                date=date.fromisoformat(entry["date"]),
                rows=int(entry.get("rows", 0)),
                first_ms=int(entry.get("first_ms", 0)),
                last_ms=int(entry.get("last_ms", 0)),
                complete=bool(entry.get("complete", False)),
                part_until=entry.get("part_until"),
                gaps=[{k: int(v) for k, v in gap.items()} for gap in entry.get("gaps", [])],
                checksum=entry.get("checksum"),
            )
        return manifest

    def update_entry(self, entry: ManifestEntry) -> None:
        self.entries[entry.date.isoformat()] = entry

    def get_entry(self, day: date) -> Optional[ManifestEntry]:
        return self.entries.get(day.isoformat())


def load_manifest(path: Path, pair: str, granularity: str) -> Manifest:
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            return Manifest.from_dict(data)
    return Manifest(pair=pair, granularity=granularity)


def save_manifest(path: Path, manifest: Manifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest.to_dict(), handle, indent=2, sort_keys=True)
