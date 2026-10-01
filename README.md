# SpaceScan

SpaceScan is an offline, uncertainty-aware baseline for turning iPhone room captures into a dimensioned plan. It accepts three input tiers—photo folders, handheld video, and Record3D LiDAR exports—and always writes the same versioned JSON contract plus an SVG plan.

> Submission status: the LiDAR path is implemented and uses raw depth, confidence, per-frame intrinsics, and poses. Photo/video paths are deterministic degraded baselines with honest wide intervals; they are not claimed to meet the assignment's accuracy gates. Opening and damage detectors are not yet implemented. See [COMPLIANCE.md](docs/COMPLIANCE.md).

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
6. Propagates geometry and pose variation into 95% intervals.

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

## Repository map

- `src/spacescan/` — ingestion, geometry, uncertainty, validation, evaluation, and rendering
- `schema/output.schema.json` — public output contract
- `benchmark/` — ground-truth template (raw captures remain outside Git)
- `docs/CAPTURE_PROTOCOL.md` — the one-page non-engineer capture route
- `docs/DEVICE_MATRIX.md` — supported hardware and claimed accuracy
- `docs/COMPLIANCE.md` — requirement-to-artifact matrix
- `docs/TECHNICAL_REPORT.md` — concise architecture and error-budget report
- `docs/FIX_LOOP.md` — before/after declaration and required measurement placeholders

## Disclosures and limitations

- Runtime dependencies: NumPy and Pillow. FFmpeg is used only to inspect video metadata.
- Capture app: Record3D by Marek Simonik. Its official feature page documents export/sharing, and the App Store listing states that LiDAR capture is supported. The evaluator should record the installed version visible on the capture phone: <https://record3d.app/features> and <https://apps.apple.com/us/app/record3d-3d-videos/id1477716895>.
- No pretrained model, hosted API, benchmark label, or incumbent-app output is used in inference.
- Monocular metric scale is mathematically underconstrained without a known object, motion/depth, or learned prior. The photo/video baseline therefore returns wide intervals rather than confident fabricated precision.

