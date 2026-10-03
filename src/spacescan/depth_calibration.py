from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median

import numpy as np
from PIL import Image

from .io import read_csv_clean, write_json
from .lidar import _discover_scan
from .metric_depth import MODEL_NAME, model_root, predict_metric_depth


def calibrate_scan(path: Path, frames: int = 6) -> tuple[list[dict], list[float], list[tuple[np.ndarray, np.ndarray]]]:
    import cv2

    scan = _discover_scan(path)
    rows = read_csv_clean(scan / "odometry.csv")
    depth_files = sorted((scan / "depth").glob("*.png"))
    count = min(len(rows), len(depth_files))
    indices = np.unique(np.linspace(0, count - 1, min(frames, count), dtype=int))
    video = cv2.VideoCapture(str(scan / "rgb.mp4"))
    details: list[dict] = []
    ratios: list[float] = []
    pairs: list[tuple[np.ndarray, np.ndarray]] = []
    for index in indices:
        video.set(cv2.CAP_PROP_POS_FRAMES, int(index))
        ok, bgr = video.read()
        if not ok:
            continue
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        # Always calibrate the raw checkpoint output. Applying an existing
        # calibration here would compound the scale on repeated runs.
        prediction = predict_metric_depth(Image.fromarray(rgb), apply_calibration=False)
        truth = np.asarray(Image.open(depth_files[int(index)]), dtype=np.float32) / 1000.0
        confidence_path = scan / "confidence" / depth_files[int(index)].name
        confidence = np.asarray(Image.open(confidence_path)) if confidence_path.exists() else np.full(truth.shape, 2)
        predicted_small = cv2.resize(prediction, (truth.shape[1], truth.shape[0]), interpolation=cv2.INTER_AREA)
        valid = (confidence >= 2) & (truth > 0.3) & (truth < 5.0) & np.isfinite(predicted_small) & (predicted_small > 0.1)
        if int(valid.sum()) < 500:
            continue
        ratio = float(np.median(truth[valid] / predicted_small[valid]))
        calibrated = predicted_small[valid] * ratio
        relative = np.abs(calibrated - truth[valid]) / truth[valid]
        ratios.append(ratio)
        # Keep a bounded, deterministic sample for global-scale evaluation.
        stride = max(1, int(valid.sum()) // 20_000)
        pairs.append((predicted_small[valid][::stride], truth[valid][::stride]))
        details.append({
            "frame": int(index),
            "valid_pixels": int(valid.sum()),
            "median_scale_truth_over_prediction": round(ratio, 5),
            "abs_rel_after_per_frame_scale": round(float(np.mean(relative)), 5),
            "delta_1_25": round(float(np.mean(np.maximum(calibrated / truth[valid], truth[valid] / calibrated) < 1.25)), 5),
        })
    video.release()
    return details, ratios, pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate metric RGB depth against synchronized supplied LiDAR")
    parser.add_argument("captures", nargs="+")
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--output", "-o", default="runs/depth_calibration.json")
    parser.add_argument("--write-calibration", action="store_true")
    args = parser.parse_args()
    all_details: list[dict] = []
    all_ratios: list[float] = []
    all_pairs: list[tuple[np.ndarray, np.ndarray]] = []
    for capture in args.captures:
        details, ratios, pairs = calibrate_scan(Path(capture), args.frames)
        all_details.append({"capture": capture, "frames": details})
        all_ratios.extend(ratios)
        all_pairs.extend(pairs)
    if not all_ratios:
        raise SystemExit("no synchronized frames could be calibrated")
    scale = float(median(all_ratios))
    global_residuals = np.concatenate([
        np.abs(prediction * scale - truth) / truth
        for prediction, truth in all_pairs
    ])
    report = {
        "model": MODEL_NAME,
        "reference": "synchronized iPhone LiDAR depth (sensor reference, not laser ground truth)",
        "captures": all_details,
        "summary": {
            "frames": len(all_ratios),
            "scale": round(scale, 6),
            "median_abs_relative_error": round(float(np.median(global_residuals)), 5),
            "relative_error_95": round(float(np.percentile(global_residuals, 95)), 5),
        },
    }
    write_json(Path(args.output), report)
    if args.write_calibration:
        payload = {
            "scale": round(scale, 6),
            "relative_error_95": round(float(np.percentile(global_residuals, 95)), 5),
            "source": "Brynz supplied synchronized RGB/LiDAR captures; not independent laser truth",
            "frames": len(all_ratios),
        }
        write_json(model_root() / "calibration.json", payload)
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
