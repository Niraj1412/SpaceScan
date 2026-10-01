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

