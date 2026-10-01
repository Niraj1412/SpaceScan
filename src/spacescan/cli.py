from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from .io import write_json
from .lidar import analyze_lidar
from .media import analyze_photos, analyze_video, is_photo_capture
from .render import render_svg
from .validate import validate_result


def detect_tier(path: Path) -> str:
    candidates = [path] + ([item for item in path.iterdir() if item.is_dir()] if path.is_dir() else [])
    if any((candidate / "depth").is_dir() and (candidate / "odometry.csv").is_file() for candidate in candidates):
        return "lidar"
    if path.is_file() and path.suffix.lower() in {".mp4", ".mov", ".m4v"}:
        return "video"
    if is_photo_capture(path):
        return "photos"
    raise ValueError("cannot infer tier; pass a Record3D folder, a video, or a folder of photos")


def run(args: argparse.Namespace) -> int:
    started = time.perf_counter()
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    tier = args.tier if args.tier != "auto" else detect_tier(input_path)
    if tier == "lidar":
        result = analyze_lidar(input_path, max_frames=args.max_frames, drift_correction=not args.no_drift_correction)
    elif tier == "photos":
        result = analyze_photos(input_path)
    else:
        result = analyze_video(input_path)
    result["diagnostics"]["runtime_seconds"] = round(time.perf_counter() - started, 3)
    errors = validate_result(result)
    if errors:
        raise ValueError("invalid output: " + "; ".join(errors))
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "result.json", result)
    render_svg(result, output_dir / "plan.svg")
    print(json.dumps({"tier": tier, "output": str(output_dir), "runtime_seconds": result["diagnostics"]["runtime_seconds"]}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="spacescan", description="Offline room geometry pipeline")
    parser.add_argument("input", help="capture folder, video, or photo folder")
    parser.add_argument("--output", "-o", default="output", help="output directory")
    parser.add_argument("--tier", choices=("auto", "photos", "video", "lidar"), default="auto")
    parser.add_argument("--max-frames", type=int, default=240, help="uniformly sampled LiDAR frames")
    parser.add_argument("--no-drift-correction", action="store_true", help="ablation: disable endpoint loop correction")
    return parser


def main() -> None:
    try:
        raise SystemExit(run(build_parser().parse_args()))
    except (ValueError, FileNotFoundError, NotImplementedError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
