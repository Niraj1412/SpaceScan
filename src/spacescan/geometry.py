from __future__ import annotations

import math
import numpy as np


def quaternion_matrix(q: np.ndarray) -> np.ndarray:
    """Return the active rotation matrix for an (x, y, z, w) quaternion."""
    x, y, z, w = q / np.linalg.norm(q)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def robust_mode(values: np.ndarray, bin_width: float = 0.02) -> tuple[float, int]:
    values = values[np.isfinite(values)]
    if len(values) == 0:
        raise ValueError("cannot estimate a mode from no values")
    lo, hi = np.percentile(values, [0.5, 99.5])
    if hi <= lo:
        return float(np.median(values)), len(values)
    bins = max(5, int(math.ceil((hi - lo) / bin_width)))
    counts, edges = np.histogram(values, bins=bins, range=(lo, hi))
    index = int(np.argmax(counts))
    center = (edges[index] + edges[index + 1]) / 2
    local = values[np.abs(values - center) <= bin_width * 1.5]
    return float(np.median(local) if len(local) else center), int(counts[index])


def dominant_manhattan_angle(points_xz: np.ndarray) -> float:
    """Find a stable property axis using projection concentration."""
    if len(points_xz) < 100:
        return 0.0
    sample = points_xz[:: max(1, len(points_xz) // 30000)]
    best_angle, best_score = 0.0, -1.0
    for degrees in np.arange(0.0, 90.0, 1.0):
        angle = math.radians(float(degrees))
        axis = np.array([math.cos(angle), math.sin(angle)])
        other = np.array([-axis[1], axis[0]])
        score = 0.0
        for direction in (axis, other):
            projected = sample @ direction
            lo, hi = np.percentile(projected, [1, 99])
            if hi - lo < 0.2:
                continue
            hist, _ = np.histogram(projected, bins=max(10, int((hi - lo) / 0.04)), range=(lo, hi))
            score += float(np.partition(hist, -min(4, len(hist)))[-min(4, len(hist)):].sum())
        if score > best_score:
            best_angle, best_score = angle, score
    return best_angle


def oriented_envelope(points_xz: np.ndarray, angle: float) -> np.ndarray:
    axis = np.array([math.cos(angle), math.sin(angle)])
    other = np.array([-axis[1], axis[0]])
    basis = np.stack([axis, other], axis=1)
    local = points_xz @ basis
    lo = np.percentile(local, 1.0, axis=0)
    hi = np.percentile(local, 99.0, axis=0)
    corners = np.array([[lo[0], lo[1]], [hi[0], lo[1]], [hi[0], hi[1]], [lo[0], hi[1]]])
    return corners @ basis.T


def polygon_area(polygon: np.ndarray) -> float:
    return float(abs(np.dot(polygon[:, 0], np.roll(polygon[:, 1], -1)) - np.dot(polygon[:, 1], np.roll(polygon[:, 0], -1))) / 2)


def deterministic_kmeans(points: np.ndarray, clusters: int, iterations: int = 40) -> tuple[np.ndarray, np.ndarray]:
    """Small dependency-free k-means with farthest-point initialization."""
    if clusters <= 1:
        return np.mean(points, axis=0, keepdims=True), np.zeros(len(points), dtype=int)
    centers = [points[len(points) // 2]]
    for _ in range(1, clusters):
        distances = np.min(np.stack([np.sum((points - center) ** 2, axis=1) for center in centers]), axis=0)
        centers.append(points[int(np.argmax(distances))])
    centers_array = np.asarray(centers, dtype=float)
    labels = np.zeros(len(points), dtype=int)
    for _ in range(iterations):
        distance_matrix = np.stack([np.sum((points - center) ** 2, axis=1) for center in centers_array], axis=1)
        new_labels = np.argmin(distance_matrix, axis=1)
        new_centers = np.stack([
            np.mean(points[new_labels == index], axis=0) if np.any(new_labels == index) else centers_array[index]
            for index in range(clusters)
        ])
        if np.array_equal(new_labels, labels) and np.allclose(new_centers, centers_array):
            labels, centers_array = new_labels, new_centers
            break
        labels, centers_array = new_labels, new_centers
    return centers_array, labels


def _clip_halfplane(polygon: np.ndarray, normal: np.ndarray, limit: float) -> np.ndarray:
    if len(polygon) == 0:
        return polygon
    output: list[np.ndarray] = []
    previous = polygon[-1]
    previous_inside = float(previous @ normal) <= limit + 1e-9
    for current in polygon:
        current_inside = float(current @ normal) <= limit + 1e-9
        if current_inside != previous_inside:
            edge = current - previous
            denominator = float(edge @ normal)
            if abs(denominator) > 1e-12:
                amount = (limit - float(previous @ normal)) / denominator
                output.append(previous + amount * edge)
        if current_inside:
            output.append(current)
        previous, previous_inside = current, current_inside
    return np.asarray(output, dtype=float)


def voronoi_partition(boundary: np.ndarray, centers: np.ndarray) -> list[np.ndarray]:
    """Clip a convex property envelope into non-overlapping nearest-center cells."""
    cells: list[np.ndarray] = []
    for index, center in enumerate(centers):
        cell = boundary.copy()
        for other_index, other in enumerate(centers):
            if other_index == index:
                continue
            normal = other - center
            limit = (float(other @ other) - float(center @ center)) / 2
            cell = _clip_halfplane(cell, normal, limit)
            if len(cell) < 3:
                break
        cells.append(cell)
    return cells
