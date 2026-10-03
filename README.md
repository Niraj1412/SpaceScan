# SpaceScan

SpaceScan is an offline, uncertainty-aware baseline for turning iPhone room captures into a dimensioned plan. It accepts three input tiers—photo folders, handheld video, and Record3D LiDAR exports—and always writes the same versioned JSON contract plus an SVG plan.

> Submission status: the LiDAR path uses raw depth, confidence, per-frame intrinsics, and poses. Photo/video paths can use a local metric-depth model, calibrated against the supplied synchronized LiDAR, but remain degraded and are not claimed to meet the assignment's accuracy gates. Opening and damage detectors are implemented conservatively and remain unverified on labelled field evidence. See [COMPLIANCE.md](docs/COMPLIANCE.md).

## Clean-machine setup (under 15 minutes)

Requirements: Python 3.10+, `pip`, and FFmpeg/ffprobe on `PATH` for video metadata. No cloud service or private infrastructure is called.

```powershell
git clone <submission-repository-url>
cd spacescan
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
spacescan <capture-path> --output runs/<capture-name>
```

For model-backed photo/video geometry, install the optional local model once:

```powershell
.\scripts\setup_metric_depth.ps1
spacescan-calibrate-depth .\single_room .\single_scan_floor_only .\single_scan_with_ceiling `
  --frames 4 --output .\runs\depth_calibration.json --write-calibration
```

The setup script downloads the official Apache-2.0 Depth Anything V2 Small indoor checkpoint and CPU runtime. Model code and weights remain ignored by Git. Inference is offline; without this bundle, photo/video processing automatically falls back to disclosed architectural priors.

macOS/Linux activation is `source .venv/bin/activate`. The result is:

```text
runs/<capture-name>/
├── result.json    # schema-versioned measurements and 95% intervals
└── plan.svg       # dimensioned property plan
```

If editable installation is unavailable, run without installation:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
python -m spacescan.cli <capture-path> --output runs/<capture-name>
```

## One command per capture

Tier detection is automatic:

```powershell
spacescan data/property_photos --output runs/photos
spacescan data/walkthrough.mov --output runs/video
spacescan data/record3d_export --output runs/lidar
```

Photo input is either one folder of images (one room), or a property folder with one image folder per room. An optional `capture.json` may declare adjacency for integration testing; measurements inserted there must not be used in a blind benchmark.

Record3D input must contain `rgb.mp4`, `depth/*.png`, `confidence/*.png`, `odometry.csv`, and `camera_matrix.csv`. `imu.csv` is retained as raw evidence. Millimetre uint16 depth and confidence value 2 are used by default.

## What the LiDAR path does

1. Uniformly samples synchronized frames and unprojects depth with per-frame intrinsics.
2. Converts Record3D optical coordinates to ARKit world coordinates.
3. Applies an endpoint loop constraint when the capture returns within 1 m of its starting marker.
4. Finds horizontal floor/ceiling plane modes and vertical wall evidence.
5. Estimates a Manhattan frame and a robust property envelope.
6. Splits property-scale trajectories into non-overlapping rooms and derives adjacency from room transitions.
7. Searches sufficiently supported wall planes for conservative door-sized gaps.
8. Propagates geometry and pose variation into 95% intervals.

Photo/video inspection uses repeated, centred colour-anomaly evidence for disclosed `mold_like_darkening` and `water_stain_like_discoloration` classes. Accepted regions generate concealed-moisture flags and surface-keyed scope items. These labels are triage signals, not material diagnosis.

Photo/video geometry uses the local Depth Anything V2 metric indoor Small model when installed. Per-frame ranges are aggregated into a room envelope; the supplied RGB/LiDAR pairs provide a single global scale check and a residual-based uncertainty width. This is model-backed evidence, not multi-view reconstruction: camera poses, exact room boundaries, and opening geometry are still unavailable in these tiers.

The plan is not a mesh screenshot: it is generated from the published structured measurements. A drift ablation is reproducible with:

```powershell
.\scripts\run_drift_ablation.ps1 -Capture data/record3d_export
```

## Ground-truth evaluation

Copy [ground_truth.example.json](benchmark/ground_truth.example.json), replace every example number with laser/tape measurements, and run:

```powershell
spacescan-evaluate runs/lidar/result.json benchmark/my_room.ground_truth.json -o runs/lidar/evaluation.json
```

The evaluator reports absolute/relative error, per-measurement gate status, and empirical 95% interval coverage. It never silently matches walls by sorted length: IDs must correspond to the measurement sketch.

## Test

```powershell
python -m unittest discover -s tests -v
```

Run the complete supplied-data reproduction suite:

```powershell
.\scripts\run_reproduction.ps1
```

Run every official Brynz sample through LiDAR, native video, and a labelled
video-frame photo smoke test:

```powershell
.\scripts\run_official_sample.ps1
```

The generated `photos-derived` rows prove interface coverage only. They are
not represented as independently captured photo-tier benchmark evidence.

## Repository map

- `src/spacescan/` — ingestion, geometry, uncertainty, validation, evaluation, and rendering
- `schema/output.schema.json` — public output contract
- `benchmark/` — ground-truth template (raw captures remain outside Git)
- `docs/CAPTURE_PROTOCOL.md` — the one-page non-engineer capture route
- `docs/DEVICE_MATRIX.md` — supported hardware and claimed accuracy
- `docs/COMPLIANCE.md` — requirement-to-artifact matrix
- `docs/TECHNICAL_REPORT.md` — concise architecture and error-budget report
- `docs/BENCHMARK_REPORT.md` — supplied-data checks and unfilled accuracy gates
- `docs/FIX_LOOP.md` — before/after declaration and required measurement placeholders

## Disclosures and limitations

- Base runtime dependencies: NumPy and Pillow. The optional model-backed path adds CPU PyTorch, torchvision, OpenCV, the official model code, and its Small indoor checkpoint. FFmpeg is used for video metadata/frame extraction.
- Capture app: Record3D by Marek Simonik. Its official feature page documents export/sharing, and the App Store listing states that LiDAR capture is supported. The evaluator should record the installed version visible on the capture phone: <https://record3d.app/features> and <https://apps.apple.com/us/app/record3d-3d-videos/id1477716895>.
- The optional pretrained model is disclosed and runs locally; no hosted inference API, benchmark label, or incumbent-app output is used.
- Monocular metric scale remains uncertain. Calibration on nine synchronized supplied frames produced 30.6% median absolute relative pixel error and a 179.9% 95th-percentile tail under one global scale. That broad residual is propagated rather than replaced with a cosmetically narrow interval; this is not an accuracy-gate pass.
