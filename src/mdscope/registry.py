"""In-memory registry of loaded systems, keyed by a deterministic system_id."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import MDAnalysis as mda


@dataclass
class System:
    system_id: str
    name: str
    topology: Path
    trajectories: list[Path]
    universe: mda.Universe
    warnings: list[str] = field(default_factory=list)


_SYSTEMS: dict[str, System] = {}


def make_id(paths: list[Path]) -> str:
    """Short hash of path + size + mtime, so the same files always get the same id."""
    h = hashlib.sha1()
    for p in paths:
        st = p.stat()
        h.update(f"{p}:{st.st_size}:{int(st.st_mtime)}\n".encode())
    return h.hexdigest()[:8]


def register(system: System) -> System:
    _SYSTEMS[system.system_id] = system
    return system


def get(system_id: str) -> System:
    try:
        return _SYSTEMS[system_id]
    except KeyError:
        known = ", ".join(f"{s.system_id} ({s.name})" for s in _SYSTEMS.values()) or "none"
        raise KeyError(f"unknown system_id {system_id!r}; loaded systems: {known}") from None


def list_systems() -> list[System]:
    return list(_SYSTEMS.values())
