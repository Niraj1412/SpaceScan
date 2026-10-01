from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Interval:
    value: float
    low: float
    high: float
    unit: str = "m"
    confidence: float = 0.95
    method: str = ""


@dataclass
class Wall:
    id: str
    start: list[float]
    end: list[float]
    length: Interval
    surface_area: Interval


@dataclass
class Opening:
    id: str
    kind: str
    wall_id: str
    offset: Interval
    width: Interval
    height: Interval
    detection_confidence: float


@dataclass
class DamageRegion:
    id: str
    surface_id: str
    damage_class: str
    polygon_uv: list[list[float]]
    area: Interval
    detection_confidence: float


@dataclass
class Room:
    id: str
    name: str
    polygon: list[list[float]]
    walls: list[Wall]
    floor_area: Interval
    ceiling_height: Interval
    openings: list[Opening] = field(default_factory=list)
    damages: list[DamageRegion] = field(default_factory=list)


def interval(value: float, half_width: float, method: str, unit: str = "m") -> Interval:
    value = float(value)
    return Interval(
        value=round(value, 4),
        low=round(max(0.0, value - half_width), 4),
        high=round(value + half_width, 4),
        unit=unit,
        method=method,
    )


def to_dict(value: Any) -> Any:
    return asdict(value)

