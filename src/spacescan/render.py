from __future__ import annotations

from html import escape
from pathlib import Path


def render_svg(result: dict, path: Path) -> None:
    rooms = result["property"]["rooms"]
    all_points = [point for room in rooms for point in room["polygon"]]
    if not all_points:
        raise ValueError("cannot render a plan with no rooms")
    xs, ys = [p[0] for p in all_points], [p[1] for p in all_points]
    scale = min(900 / max(max(xs) - min(xs), 1), 650 / max(max(ys) - min(ys), 1))
    margin = 70
    width, height = 1040, 790
    def xy(point: list[float]) -> tuple[float, float]:
        return margin + (point[0] - min(xs)) * scale, height - margin - (point[1] - min(ys)) * scale
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#172033}.room{fill:#dcecff;stroke:#172033;stroke-width:5}.dim{font-size:16px}.name{font-size:24px;font-weight:bold}</style>',
    ]
    for room in rooms:
        polygon = room["polygon"]
        rendered = " ".join(f"{x:.1f},{y:.1f}" for x, y in map(xy, polygon))
        parts.append(f'<polygon class="room" points="{rendered}"/>')
        center_x = sum(xy(p)[0] for p in polygon) / len(polygon)
        center_y = sum(xy(p)[1] for p in polygon) / len(polygon)
        area = room["floor_area"]
        parts.append(f'<text class="name" x="{center_x:.1f}" y="{center_y:.1f}" text-anchor="middle">{escape(room["name"])}</text>')
        parts.append(f'<text class="dim" x="{center_x:.1f}" y="{center_y+26:.1f}" text-anchor="middle">{area["value"]:.2f} m² [{area["low"]:.2f}, {area["high"]:.2f}]</text>')
        for wall in room["walls"]:
            a, b = xy(wall["start"]), xy(wall["end"])
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            length = wall["length"]
            parts.append(f'<text class="dim" x="{mx:.1f}" y="{my-8:.1f}" text-anchor="middle">{length["value"]:.2f} m</text>')
    parts.append(f'<text x="30" y="35" font-size="20">SpaceScan · {escape(result["capture"]["tier"].upper())} · 95% intervals</text>')
    parts.append('</svg>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")

