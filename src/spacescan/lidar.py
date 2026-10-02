from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import numpy as np
from PIL import Image

from .geometry import deterministic_kmeans, dominant_manhattan_angle, oriented_envelope, polygon_area, quaternion_matrix, robust_mode, voronoi_partition
from .io import read_csv_clean
from .inspection import derive_claims, detect_lidar_openings
from .models import Room, Wall, interval, to_dict


@dataclass
class Cloud:
    points: np.ndarray
    horizontal: np.ndarray
    vertical: np.ndarray
    trajectory: np.ndarray
    used_frames: int
    available_frames: int
    loop_closure_applied: bool
    endpoint_error_m: float


def _discover_scan(path: Path) -> Path:
    candidates = [path] + [item for item in path.iterdir() if item.is_dir()] if path.is_dir() else []
    for candidate in candidates:
        if (candidate / "depth").is_dir() and (candidate / "odometry.csv").is_file():
            return candidate
    raise ValueError(f"{path} is not a LiDAR capture (expected depth/ and odometry.csv)")


def build_cloud(input_path: Path, max_frames: int = 240, pixel_step: int = 4, drift_correction: bool = True) -> tuple[Path, Cloud]:
    scan = _discover_scan(input_path)
    rows = read_csv_clean(scan / "odometry.csv")
    depth_files = sorted((scan / "depth").glob("*.png"))
    if not rows or not depth_files:
        raise ValueError("capture contains no synchronized depth and pose frames")
    count = min(len(rows), len(depth_files))
    indices = np.unique(np.linspace(0, count - 1, min(max_frames, count), dtype=int))
    point_parts: list[np.ndarray] = []
    horizontal_parts: list[np.ndarray] = []
    vertical_parts: list[np.ndarray] = []
    trajectory: list[np.ndarray] = []
    all_translations = np.array([[float(row[key]) for key in ("x", "y", "z")] for row in rows])
    endpoint_delta = all_translations[-1] - all_translations[0]
    horizontal_span = float(np.linalg.norm(np.ptp(all_translations[:, [0, 2]], axis=0)))
    endpoint_error = float(np.linalg.norm(endpoint_delta))
    close_loop = bool(drift_correction and horizontal_span > 2.5 and endpoint_error < 1.0)

    for index in indices:
        row = rows[int(index)]
        depth = np.asarray(Image.open(depth_files[int(index)]), dtype=np.float64) / 1000.0
        confidence_path = scan / "confidence" / depth_files[int(index)].name
        confidence = np.asarray(Image.open(confidence_path)) if confidence_path.exists() else np.full(depth.shape, 2)
        height, width = depth.shape
        yy, xx = np.mgrid[0:height:pixel_step, 0:width:pixel_step]
        z = depth[::pixel_step, ::pixel_step]
        conf = confidence[::pixel_step, ::pixel_step]
        scale_x, scale_y = width / 1920.0, height / 1440.0
        fx, fy = float(row["fx"]) * scale_x, float(row["fy"]) * scale_y
        cx, cy = float(row["cx"]) * scale_x, float(row["cy"]) * scale_y
        image_x = (xx - cx) * z / fx
        image_y = (yy - cy) * z / fy
        # Record3D exports optical +Z depth. Image Y points down while the
        # pose's camera Y points up, hence the sign flip on image_y.
        camera = np.stack([image_x, -image_y, z], axis=-1)
        valid = (conf >= 2) & (z > 0.20) & (z < 5.0)

        rotation = quaternion_matrix(np.array([float(row[key]) for key in ("qx", "qy", "qz", "qw")]))
        translation = np.array([float(row[key]) for key in ("x", "y", "z")])
        if close_loop:
            # The capture protocol ends at the start marker. Distribute the
            # residual endpoint error along the path (a lightweight pose-graph
            # endpoint constraint) before plane anchoring.
            alpha = float(index) / max(1, count - 1)
            translation = translation - alpha * endpoint_delta
        world = camera @ rotation.T + translation

        # Approximate local surface normals before masking. Cross-products survive rotation.
        gy = np.gradient(camera, axis=0)
        gx = np.gradient(camera, axis=1)
        normals = np.cross(gx, gy)
        norm = np.linalg.norm(normals, axis=-1, keepdims=True)
        normals = np.divide(normals, norm, out=np.zeros_like(normals), where=norm > 1e-9) @ rotation.T
        ny = np.abs(normals[..., 1])
        point_parts.append(world[valid])
        horizontal_parts.append(world[valid & (ny > 0.88)])
        vertical_parts.append(world[valid & (ny < 0.25)])
        trajectory.append(translation)

    return scan, Cloud(
        points=np.concatenate(point_parts),
        horizontal=np.concatenate(horizontal_parts),
        vertical=np.concatenate(vertical_parts),
        trajectory=np.stack(trajectory),
        used_frames=len(indices),
        available_frames=count,
        loop_closure_applied=close_loop,
        endpoint_error_m=endpoint_error,
    )


def _floor_ceiling(cloud: Cloud) -> tuple[float, float, str]:
    ys = cloud.horizontal[:, 1]
    camera_y = float(np.median(cloud.trajectory[:, 1]))
    below = ys[(ys < camera_y - 0.45) & (ys > camera_y - 2.2)]
    above = ys[(ys > camera_y + 0.45) & (ys < camera_y + 2.5)]
    floor = robust_mode(below, 0.025)[0] if len(below) > 100 else float(np.percentile(cloud.points[:, 1], 2))
    if len(above) > 100:
        ceiling = robust_mode(above, 0.025)[0]
        method = "horizontal-plane modes"
    else:
        ceiling = floor + 2.45
        method = "floor plane + residential height prior"
    height = ceiling - floor
    if not 1.8 <= height <= 4.5:
        ceiling, method = floor + 2.45, "floor plane + residential height prior"
    return floor, ceiling, method


def analyze_lidar(input_path: Path, max_frames: int = 240, drift_correction: bool = True) -> dict:
    scan, cloud = build_cloud(input_path, max_frames=max_frames, drift_correction=drift_correction)
    floor, ceiling, height_method = _floor_ceiling(cloud)
    vertical = cloud.vertical
    band = vertical[(vertical[:, 1] > floor + 0.15) & (vertical[:, 1] < ceiling - 0.15)]
    plan_points = band[:, [0, 2]] if len(band) >= 500 else cloud.points[:, [0, 2]]
    angle = dominant_manhattan_angle(plan_points)
    polygon = oriented_envelope(plan_points, angle)
    ceiling_height = ceiling - floor
    area = polygon_area(polygon)
    # Until residuals are calibrated on held-out laser truth, do not emit a
    # centimetre-level interval simply because the fitted planes look sharp.
    loop_term = cloud.endpoint_error_m * 0.15 if cloud.loop_closure_applied else 0.0
    geometry_uncertainty = max(0.03, loop_term, float(np.std(cloud.trajectory[:, 1])) * 0.35)
    ceiling_uncertainty = 0.02 if height_method == "horizontal-plane modes" else 0.25
    property_scale = area >= 60 and min(np.ptp(cloud.trajectory[:, [0, 2]], axis=0)) >= 5.5
    requested_rooms = min(5, max(2, int(round(area / 28.0)))) if property_scale else 1
    if requested_rooms > 1:
        centers, labels = deterministic_kmeans(cloud.trajectory[:, [0, 2]], requested_rooms)
        cells = voronoi_partition(polygon, centers)
    else:
        centers = np.mean(cloud.trajectory[:, [0, 2]], axis=0, keepdims=True)
        labels = np.zeros(len(cloud.trajectory), dtype=int)
        cells = [polygon]

    rooms: list[Room] = []
    center_to_room: dict[int, str] = {}
    for center_index, cell in enumerate(cells):
        cell_area = polygon_area(cell) if len(cell) >= 3 else 0.0
        if cell_area < 2.0:
            continue
        room_index = len(rooms) + 1
        room_id = f"room-{room_index}"
        center_to_room[center_index] = room_id
        cell_dimensions = np.linalg.norm(np.roll(cell, -1, axis=0) - cell, axis=1)
        walls: list[Wall] = []
        for wall_index, (start, end, length) in enumerate(zip(cell, np.roll(cell, -1, axis=0), cell_dimensions), start=1):
            wall_id = f"{room_id}-wall-{wall_index}"
            walls.append(Wall(
                id=wall_id,
                start=[round(float(x), 4) for x in start],
                end=[round(float(x), 4) for x in end],
                length=interval(float(length), geometry_uncertainty, "LiDAR wall-envelope/Voronoi partition"),
                surface_area=interval(float(length * ceiling_height), max(0.08, length * ceiling_uncertainty), "propagated wall × height", "m2"),
            ))
        room = Room(
            id=room_id,
            name=f"Room {room_index}",
            polygon=[[round(float(x), 4) for x in point] for point in cell],
            walls=walls,
            floor_area=interval(cell_area, max(0.08, cell_area * 0.04), "LiDAR property partition", "m2"),
            ceiling_height=interval(ceiling_height, ceiling_uncertainty, height_method),
        )
        room.openings = detect_lidar_openings(cell, walls, vertical, floor, ceiling, geometry_uncertainty)
        rooms.append(room)

    adjacency_pairs: dict[tuple[str, str], int] = {}
    for first, second in zip(labels, labels[1:]):
        if first == second or int(first) not in center_to_room or int(second) not in center_to_room:
            continue
        pair = tuple(sorted((center_to_room[int(first)], center_to_room[int(second)])))
        adjacency_pairs[pair] = adjacency_pairs.get(pair, 0) + 1
    adjacencies = [
        {"room_a": pair[0], "room_b": pair[1], "confidence": round(min(0.9, 0.55 + count * 0.04), 3), "method": "trajectory transition across non-overlapping property partition"}
        for pair, count in sorted(adjacency_pairs.items())
    ]
    concealed, scope = derive_claims(rooms)
    capture_hash = hashlib.sha256((scan / "odometry.csv").read_bytes()).hexdigest()[:16]
    return {
        "schema_version": "1.0.0",
        "capture": {"id": capture_hash, "tier": "lidar", "source": str(input_path), "units": "metric"},
        "property": {
            "rooms": [to_dict(room) for room in rooms],
            "adjacencies": adjacencies,
            "footprint_area": to_dict(interval(area, max(0.08, area * 0.025), "LiDAR property envelope", "m2")),
        },
        "concealed_damage_flags": concealed,
        "scope_line_items": scope,
        "diagnostics": {
            "status": "baseline",
            "frames_available": cloud.available_frames,
            "frames_used": cloud.used_frames,
            "points_used": int(len(cloud.points)),
            "drift_correction": "endpoint loop constraint + Manhattan plane anchoring" if cloud.loop_closure_applied else "Manhattan plane anchoring (no closed loop detected)",
            "endpoint_error_m": round(cloud.endpoint_error_m, 4),
            "loop_closure_applied": cloud.loop_closure_applied,
            "dominant_axis_degrees": round(float(np.degrees(angle)), 2),
            "room_split_method": "trajectory k-means + clipped Voronoi partition" if requested_rooms > 1 else "single-room envelope",
            "limitations": [
                "Opening inference is conservative wall-gap evidence; validate all misses and phantoms against ground truth.",
                "RGB damage inference is not enabled on the LiDAR path in this baseline.",
                "Property-scale room splitting is trajectory/Voronoi evidence and must be checked against doorway ground truth.",
            ],
        },
    }
