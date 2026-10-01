from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageStat

from .geometry import polygon_area
from .models import Room, Wall, interval, to_dict


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def _images(path: Path) -> list[Path]:
    return sorted(item for item in path.iterdir() if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES)


def _room_folders(path: Path) -> list[tuple[str, list[Path]]]:
    direct = _images(path)
    if direct:
        return [(path.name or "room-1", direct)]
    rooms = [(folder.name, _images(folder)) for folder in sorted(path.iterdir()) if folder.is_dir()]
    return [(name, images) for name, images in rooms if images]


def is_photo_capture(path: Path) -> bool:
    """Return True for either a flat room folder or property/room/image layout."""
    if not path.is_dir():
        return False
    if _images(path):
        return True
    return any(_images(folder) for folder in path.iterdir() if folder.is_dir())


def _measurement_width(tier: str, value: float) -> float:
    fraction = 0.40 if tier == "photos" else 0.25
    return max(0.35, value * fraction)


def _make_room(index: int, name: str, width: float, length: float, x_offset: float, tier: str) -> Room:
    polygon = [[x_offset, 0.0], [x_offset + width, 0.0], [x_offset + width, length], [x_offset, length]]
    height = 2.45
    walls: list[Wall] = []
    for wall_index, (start, end, wall_length) in enumerate(
        zip(polygon, polygon[1:] + polygon[:1], (width, length, width, length)), start=1
    ):
        half = _measurement_width(tier, wall_length)
        walls.append(Wall(
            id=f"room-{index}-wall-{wall_index}",
            start=start,
            end=end,
            length=interval(wall_length, half, f"{tier} monocular prior"),
            surface_area=interval(wall_length * height, half * height + wall_length * 0.25, "propagated monocular prior", "m2"),
        ))
    area = polygon_area(np.asarray(polygon))
    return Room(
        id=f"room-{index}",
        name=name,
        polygon=polygon,
        walls=walls,
        floor_area=interval(area, _measurement_width(tier, area), f"{tier} monocular prior", "m2"),
        ceiling_height=interval(height, 0.45 if tier == "photos" else 0.30, f"{tier} residential prior"),
    )


def _manifest(path: Path) -> dict:
    manifest = path / "capture.json"
    return json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}


def analyze_photos(input_path: Path) -> dict:
    folders = _room_folders(input_path)
    if not folders:
        raise ValueError("photo capture contains no supported images")
    config = _manifest(input_path)
    configured = {room["name"]: room for room in config.get("rooms", [])}
    rooms: list[Room] = []
    x_offset = 0.0
    quality: list[dict] = []
    hash_state = hashlib.sha256()
    for index, (name, images) in enumerate(folders, start=1):
        sizes, brightness = [], []
        for image_path in images:
            hash_state.update(image_path.read_bytes())
            try:
                with Image.open(image_path) as image:
                    sizes.append(image.size)
                    brightness.append(float(ImageStat.Stat(image.convert("L").resize((64, 64))).mean[0]))
            except (OSError, ValueError):
                continue
        hint = configured.get(name, {})
        width = float(hint.get("width_m", 3.6))
        length = float(hint.get("length_m", 3.2))
        rooms.append(_make_room(index, name, width, length, x_offset, "photos"))
        x_offset += width + 0.15
        quality.append({"room": name, "images": len(images), "decoded": len(sizes), "mean_brightness": round(sum(brightness) / max(1, len(brightness)), 1)})
    adjacencies = config.get("adjacencies") or [
        {"room_a": rooms[i].id, "room_b": rooms[i + 1].id, "confidence": 0.25, "method": "folder-order fallback"}
        for i in range(len(rooms) - 1)
    ]
    total_area = sum(room.floor_area.value for room in rooms)
    return _media_result(input_path, "photos", rooms, adjacencies, hash_state.hexdigest()[:16], quality, total_area)


def _video_metadata(path: Path) -> dict:
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration,nb_frames,r_frame_rate",
        "-of", "json", str(path),
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        return json.loads(completed.stdout).get("streams", [{}])[0]
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError):
        return {}


def analyze_video(input_path: Path) -> dict:
    metadata = _video_metadata(input_path)
    room = _make_room(1, input_path.stem, 3.8, 3.4, 0.0, "video")
    digest = hashlib.sha256(input_path.read_bytes()).hexdigest()[:16]
    return _media_result(input_path, "video", [room], [], digest, [metadata], room.floor_area.value)


def _media_result(input_path: Path, tier: str, rooms: list[Room], adjacencies: list[dict], digest: str, quality: list[dict], total_area: float) -> dict:
    uncertainty = _measurement_width(tier, total_area)
    return {
        "schema_version": "1.0.0",
        "capture": {"id": digest, "tier": tier, "source": str(input_path), "units": "metric"},
        "property": {
            "rooms": [to_dict(room) for room in rooms],
            "adjacencies": adjacencies,
            "footprint_area": to_dict(interval(total_area, uncertainty, f"{tier} aggregate prior", "m2")),
        },
        "concealed_damage_flags": [],
        "scope_line_items": [],
        "diagnostics": {
            "status": "degraded-baseline",
            "input_quality": quality,
            "drift_correction": "not applicable to unordered photos" if tier == "photos" else "visual loop closure unavailable in baseline",
            "limitations": [
                "Absolute scale is unobservable from unconstrained monocular input; intervals therefore expose the architectural prior.",
                "Provide capture.json room dimensions only for pipeline integration tests, never for a blind accuracy benchmark.",
                "Opening and damage inference require the optional disclosed model bundle and are empty in this dependency-light baseline.",
            ],
        },
    }
