from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
from PIL import Image


MODEL_NAME = "Depth Anything V2 Metric Indoor Small (Hypersim/vits)"
MODEL_SOURCE = "https://github.com/DepthAnything/Depth-Anything-V2"


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def model_root() -> Path:
    configured = os.environ.get("SPACESCAN_MODEL_ROOT")
    return Path(configured).resolve() if configured else repository_root() / ".models"


def model_paths() -> tuple[Path, Path]:
    root = model_root()
    code = root / "Depth-Anything-V2" / "metric_depth"
    checkpoint = root / "checkpoints" / "depth_anything_v2_metric_hypersim_vits.pth"
    return code, checkpoint


def is_available() -> bool:
    code, checkpoint = model_paths()
    if not (code / "depth_anything_v2" / "dpt.py").is_file() or not checkpoint.is_file():
        return False
    try:
        import cv2  # noqa: F401
        import torch  # noqa: F401
    except ImportError:
        return False
    return True


class MetricDepthUnavailable(RuntimeError):
    pass


_MODEL = None


def load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if not is_available():
        raise MetricDepthUnavailable("metric-depth bundle is unavailable; run scripts/setup_metric_depth.ps1")
    code, checkpoint = model_paths()
    sys.path.insert(0, str(code))
    import torch
    from depth_anything_v2.dpt import DepthAnythingV2

    model = DepthAnythingV2(
        encoder="vits",
        features=64,
        out_channels=[48, 96, 192, 384],
        max_depth=20,
    )
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    _MODEL = model
    return model


def calibration() -> dict:
    path = model_root() / "calibration.json"
    if not path.exists():
        return {"scale": 1.0, "relative_error_95": 0.30, "source": "uncalibrated model prior"}
    return json.loads(path.read_text(encoding="utf-8"))


def predict_metric_depth(
    image: Image.Image,
    input_size: int = 384,
    *,
    apply_calibration: bool = True,
) -> np.ndarray:
    import cv2

    rgb = np.asarray(image.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    with __import__("torch").inference_mode():
        depth = load_model().infer_image(bgr, input_size=input_size)
    scale = float(calibration().get("scale", 1.0)) if apply_calibration else 1.0
    return np.asarray(depth, dtype=np.float32) * scale


def focal_pixels(image: Image.Image) -> float:
    width = image.width
    try:
        exif = image.getexif()
        focal_35 = float(exif.get(41989, 0) or 0)  # FocalLengthIn35mmFilm
        if focal_35 > 0:
            return width * focal_35 / 36.0
    except (TypeError, ValueError):
        pass
    return width * 0.72


@dataclass
class MetricRoomEstimate:
    width_m: float
    length_m: float
    uncertainty_fraction: float
    frames_used: int
    diagnostics: dict


def estimate_room_dimensions(images: Iterable[Image.Image]) -> MetricRoomEstimate:
    summaries: list[dict] = []
    for image in images:
        depth = predict_metric_depth(image)
        height, width = depth.shape
        step = max(1, min(height, width) // 180)
        yy, xx = np.mgrid[0:height:step, 0:width:step]
        sampled = depth[::step, ::step]
        valid = np.isfinite(sampled) & (sampled > 0.30) & (sampled < 15.0)
        if int(valid.sum()) < 100:
            continue
        fx = focal_pixels(image)
        x = (xx - width / 2) * sampled / fx
        central = valid & (np.abs(xx - width / 2) < width * 0.35) & (np.abs(yy - height / 2) < height * 0.38)
        values = sampled[central] if int(central.sum()) >= 100 else sampled[valid]
        lateral = x[valid]
        summaries.append({
            "far_depth_m": float(np.percentile(values, 90)),
            "lateral_span_m": float(np.percentile(lateral, 95) - np.percentile(lateral, 5)),
            "median_depth_m": float(np.median(values)),
        })
    if not summaries:
        raise MetricDepthUnavailable("metric-depth model produced no valid indoor depth samples")

    far = np.array([item["far_depth_m"] for item in summaries])
    lateral = np.array([item["lateral_span_m"] for item in summaries])
    # With perimeter/corner coverage, twice the upper-quartile visible range
    # approximates the opposite-wall span. Lateral evidence stabilizes the
    # shorter dimension without pretending camera poses are known.
    long_side = float(np.clip(2.0 * np.percentile(far, 75), 2.0, 18.0))
    short_evidence = max(float(2.0 * np.percentile(lateral, 65)), long_side * 0.55)
    short_side = float(np.clip(min(short_evidence, long_side), 1.8, 18.0))
    cal = calibration()
    # Preserve a poor calibration result instead of laundering it into a
    # plausible-looking narrow interval. The upper bound only prevents
    # pathological files from making downstream renderers unusable.
    uncertainty = float(np.clip(cal.get("relative_error_95", 0.30), 0.12, 2.00))
    return MetricRoomEstimate(
        width_m=round(short_side, 4),
        length_m=round(long_side, 4),
        uncertainty_fraction=uncertainty,
        frames_used=len(summaries),
        diagnostics={
            "model": MODEL_NAME,
            "model_source": MODEL_SOURCE,
            "calibration": cal,
            "per_frame": summaries,
            "aggregation": "2× upper-quartile metric range + lateral point-cloud span",
        },
    )
