from __future__ import annotations

from io import BytesIO
from pathlib import Path
import math
import subprocess

import numpy as np
from PIL import Image

from .models import DamageRegion, Opening, Room, interval


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    padded = np.r_[False, mask.astype(bool), False]
    changes = np.flatnonzero(padded[1:] != padded[:-1])
    return [(int(a), int(b)) for a, b in changes.reshape(-1, 2)]


def detect_lidar_openings(
    polygon: np.ndarray,
    walls: list,
    vertical_points: np.ndarray,
    floor: float,
    ceiling: float,
    uncertainty: float,
) -> list[Opening]:
    """Detect wall gaps with lower/middle absence and lintel support.

    The detector is deliberately conservative. It requires dense wall support,
    excludes corners, and reports at most one candidate per wall.
    """
    height = ceiling - floor
    if len(vertical_points) < 5000 or height < 1.8:
        return []
    detections: list[Opening] = []
    for wall, start, end in zip(walls, polygon, np.roll(polygon, -1, axis=0)):
        vector = end - start
        length = float(np.linalg.norm(vector))
        if length < 1.2:
            continue
        direction = vector / length
        normal = np.array([-direction[1], direction[0]])
        xz = vertical_points[:, [0, 2]]
        relative = xz - start
        along = relative @ direction
        distance = np.abs(relative @ normal)
        y = vertical_points[:, 1] - floor
        selected = (distance < 0.10) & (along > 0.20) & (along < length - 0.20) & (y > 0.08) & (y < height - 0.05)
        if int(selected.sum()) < max(800, int(length * 180)):
            continue
        bin_width = 0.08
        bins = max(12, int(math.ceil(length / bin_width)))
        lower = np.histogram(along[selected & (y < min(0.75, height * 0.35))], bins=bins, range=(0, length))[0]
        middle = np.histogram(along[selected & (y >= min(0.75, height * 0.35)) & (y < min(1.95, height * 0.82))], bins=bins, range=(0, length))[0]
        upper = np.histogram(along[selected & (y >= min(1.95, height * 0.82))], bins=bins, range=(0, length))[0]
        total = lower + middle + upper
        # Coverage is binary here; density variation comes from bin/grid
        # alignment and must not make every third well-observed bin look empty.
        supported = total > 2
        wall_support = float(np.mean(supported))
        if wall_support < 0.55:
            continue
        lower_cut = max(1.0, float(np.median(lower[supported])) * 0.22)
        middle_cut = max(1.0, float(np.median(middle[supported])) * 0.22)
        upper_support = max(1.0, float(np.median(upper[supported])) * 0.30)
        candidate = (lower <= lower_cut) & (middle <= middle_cut) & (upper >= upper_support)
        corner_bins = max(2, int(0.28 / (length / bins)))
        candidate[:corner_bins] = False
        candidate[-corner_bins:] = False
        valid_runs = []
        for begin, finish in _runs(candidate):
            width = (finish - begin) * length / bins
            if 0.55 <= width <= 1.85:
                valid_runs.append((begin, finish, width))
        if not valid_runs:
            continue
        begin, finish, width = max(valid_runs, key=lambda item: item[2])
        offset = (begin + finish) * 0.5 * length / bins
        confidence = min(0.88, 0.45 + 0.35 * wall_support + 0.08 * min(1.0, int(selected.sum()) / 3000))
        detections.append(Opening(
            id=f"{wall.id}-opening-1",
            kind="door",
            wall_id=wall.id,
            offset=interval(offset, max(uncertainty, bin_width), "wall-gap histogram"),
            width=interval(width, max(uncertainty, bin_width), "wall-gap histogram"),
            height=interval(min(2.05, height - 0.12), 0.12, "lintel-support estimate"),
            detection_confidence=round(confidence, 3),
        ))
    return detections


def detect_damage_regions(images: list[Image.Image], room: Room, tier: str) -> list[DamageRegion]:
    """Find conservative colour anomalies; intended as a disclosed baseline.

    Regions are emitted only for localized anomalies (not general shadows or
    underexposure). Metric area is propagated from the associated wall area.
    """
    candidates: list[tuple[float, str, list[list[float]], float, int]] = []
    for image_index, source in enumerate(images):
        rgb = np.asarray(source.convert("RGB").resize((160, 120)), dtype=np.float32)
        luminance = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
        global_luma = float(np.median(luminance))
        if global_luma < 45 or global_luma > 235:
            continue
        block_h, block_w = 10, 10
        blocks = rgb.reshape(12, block_h, 16, block_w, 3).mean(axis=(1, 3))
        block_luma = 0.2126 * blocks[..., 0] + 0.7152 * blocks[..., 1] + 0.0722 * blocks[..., 2]
        dark = block_luma < global_luma - 52
        stain = (blocks[..., 0] > blocks[..., 2] + 30) & (blocks[..., 1] > blocks[..., 2] + 12) & (block_luma < global_luma - 18)
        for label, mask in (("mold_like_darkening", dark), ("water_stain_like_discoloration", stain)):
            fraction = float(mask.mean())
            if not 0.012 <= fraction <= 0.18:
                continue
            yy, xx = np.where(mask)
            if len(xx) < 3:
                continue
            x0, x1 = float(xx.min() / 16), float((xx.max() + 1) / 16)
            y0, y1 = float(yy.min() / 12), float((yy.max() + 1) / 12)
            # Border-connected regions are overwhelmingly furniture, floor,
            # ceiling, windows, or exposure falloff rather than localized wall
            # damage. The capture protocol asks operators to centre damage.
            if x0 <= 0.03 or x1 >= 0.97 or y0 <= 0.03 or y1 >= 0.97:
                continue
            contrast = float(global_luma - np.mean(block_luma[mask]))
            confidence = min(0.78, 0.42 + contrast / 220 + min(fraction, 0.08))
            candidates.append((confidence, label, [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], fraction, image_index))
    if not candidates or not room.walls:
        return []
    # Avoid flooding scope with correlated frames; retain strongest class evidence.
    result: list[DamageRegion] = []
    for label in sorted({candidate[1] for candidate in candidates}):
        class_candidates = [c for c in candidates if c[1] == label]
        if len({candidate[4] for candidate in class_candidates}) < 2:
            continue
        confidence, _, polygon, fraction, image_index = max(class_candidates, key=lambda c: c[0])
        wall = room.walls[image_index % len(room.walls)]
        area = wall.surface_area.value * fraction
        relative_uncertainty = 0.65 if tier == "photos" else 0.50
        result.append(DamageRegion(
            id=f"{room.id}-damage-{len(result) + 1}",
            surface_id=wall.id,
            damage_class=label,
            polygon_uv=polygon,
            area=interval(area, max(0.05, area * relative_uncertainty), f"{tier} image anomaly projection", "m2"),
            detection_confidence=round(confidence, 3),
        ))
    return result


def sample_video_frames(path: Path, duration: float, count: int = 8) -> list[Image.Image]:
    if duration <= 0:
        return []
    frames: list[Image.Image] = []
    for timestamp in np.linspace(duration * 0.08, duration * 0.92, count):
        command = ["ffmpeg", "-loglevel", "error", "-ss", f"{timestamp:.3f}", "-i", str(path), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"]
        try:
            completed = subprocess.run(command, check=True, capture_output=True)
            with Image.open(BytesIO(completed.stdout)) as image:
                frames.append(image.convert("RGB").copy())
        except (FileNotFoundError, subprocess.CalledProcessError, OSError):
            continue
    return frames


def derive_claims(rooms: list[Room]) -> tuple[list[dict], list[dict]]:
    concealed: list[dict] = []
    scope: list[dict] = []
    for room in rooms:
        for damage in room.damages:
            scope.append({
                "id": f"scope-{len(scope) + 1}",
                "surface_id": damage.surface_id,
                "action": "inspect, isolate, clean and refinish affected surface",
                "quantity": damage.area.value,
                "unit": "m2",
                "source_damage_id": damage.id,
                "confidence": damage.detection_confidence,
            })
            if damage.damage_class in {"mold_like_darkening", "water_stain_like_discoloration"}:
                concealed.append({
                    "id": f"concealed-{len(concealed) + 1}",
                    "surface_id": damage.surface_id,
                    "flag": "possible_concealed_moisture",
                    "rule": "visible moisture-like discoloration or mold-like darkening; inspect behind finish before scope finalization",
                    "source_damage_id": damage.id,
                    "confidence": round(damage.detection_confidence * 0.85, 3),
                })
    return concealed, scope
