# SpaceScan

SpaceScan is an offline, uncertainty-aware prototype that turns room captures into a structured, dimensioned property plan. It accepts photo folders, handheld video, and Record3D LiDAR exports through one command and writes the same versioned JSON contract plus an SVG plan for every tier.

This repository is an Applied AI Engineer take-home submission. It prioritizes reproducibility and explicit failure reporting: unsupported evidence produces wider intervals or a documented miss rather than fabricated precision.

## Status

| Capability | Status |
|---|---|
| Photo-folder ingestion and whole-property layout | Implemented; metric accuracy gate not met |
| Video ingestion and metric-depth envelope | Implemented; multi-room pose graph not available |
| Record3D depth, confidence, intrinsics, and poses | Implemented |
| Floor/ceiling planes and room measurements | Implemented; rectangular/Voronoi approximation |
| Multi-room adjacency | Implemented from trajectory or declared photo manifest |
| Drift correction and on/off ablation | Implemented |
| Conservative opening and damage inference | Implemented; field recall remains unverified |
| Measurement intervals, JSON schema, and SVG plan | Implemented |
| Ground-truth and opening miss/phantom evaluation | Implemented |

See the [compliance matrix](docs/COMPLIANCE.md) and [benchmark report](docs/BENCHMARK_REPORT.md) for requirement-level status and measured failures.

## Quick start

Requirements:

- Python 3.10 or newer
- Git and `pip`
- FFmpeg/ffprobe on `PATH` for video inspection and sample extraction
- Windows PowerShell for the provided setup and reproduction scripts

```powershell
git clone <repository-url>
cd spacescan
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
```

The base package depends only on NumPy and Pillow. It runs without a network service.

### Optional model-backed photo/video geometry

Install the pinned Depth Anything V2 Metric Indoor Small model and CPU runtime:

```powershell
.\scripts\setup_metric_depth.ps1
```

The script checks out a pinned official model revision and verifies the checkpoint SHA-256. Model code and weights are kept outside Git. Without this bundle, photo/video processing falls back to clearly labelled architectural priors.

If synchronized RGB/LiDAR captures are available, calibrate the model before RGB evaluation:

```powershell
spacescan-calibrate-depth `
  .\single_room `
  .\single_scan_floor_only `
  .\single_scan_with_ceiling `
  --frames 4 `
  --output .\runs\depth_calibration.json `
  --write-calibration
```

## Run a capture

Tier detection is automatic:

```powershell
spacescan .\data\property_photos --output .\runs\photos
spacescan .\data\walkthrough.mp4 --output .\runs\video
spacescan .\data\record3d_export --output .\runs\lidar
```

Each run produces:

```text
runs/<capture>/
|-- result.json   # schema-versioned measurements and 95% intervals
`-- plan.svg      # plan rendered only from the structured result
```

The JSON contract is published at [schema/output.schema.json](schema/output.schema.json).

### Photo layout

Use one directory per room:

```text
property_photos/
|-- 01_entrance/
|-- 02_corridor/
`-- 03_bedroom/
```

An optional `capture.json` can merge evidence folders and declare known adjacency without supplying benchmark dimensions:

```json
{
  "rooms": [
    {"name": "01_entrance", "folders": ["01_entrance"]},
    {"name": "02_corridor", "folders": ["02_corridor"]},
    {"name": "03_bedroom", "folders": ["03_bedroom", "04_damage"]}
  ],
  "adjacencies": [
    {
      "room_a": "room-1",
      "room_b": "room-2",
      "confidence": 0.9,
      "method": "operator-declared connection"
    }
  ]
}
```

### Record3D layout

The LiDAR input directory must contain:

```text
record3d_export/
|-- rgb.mp4
|-- odometry.csv
|-- camera_matrix.csv
|-- imu.csv
|-- depth/
`-- confidence/
```

Depth is interpreted as millimetre uint16 data; confidence value 2 is used by default.

## Pipeline

The LiDAR path:

1. Uniformly samples synchronized frames.
2. Unprojects high-confidence depth with per-frame intrinsics.
3. Converts the Record3D optical basis into ARKit world coordinates.
4. Applies a horizontal endpoint loop constraint when the capture closes.
5. Extracts floor/ceiling modes and vertical wall evidence.
6. Estimates a Manhattan frame and robust property envelope.
7. Partitions property-scale trajectories into non-overlapping rooms.
8. Derives adjacency, searches for supported door-sized gaps, and propagates uncertainty.

Photo/video geometry uses local metric-depth estimates when installed. It aggregates per-frame range and lateral evidence but does not claim full structure-from-motion or known camera poses. Repeated centered color anomalies can produce disclosed `mold_like_darkening` or `water_stain_like_discoloration` triage regions, concealed-moisture flags, and surface-keyed scope items. These are not material diagnoses.

## Evaluation and reproduction

Copy the ground-truth template, replace only values you measured, and keep room/wall IDs aligned with the measurement sketch:

```powershell
Copy-Item .\benchmark\ground_truth.example.json .\benchmark\my_ground_truth.json
spacescan-evaluate `
  .\runs\photos\result.json `
  .\benchmark\my_ground_truth.json `
  --output .\runs\photos\evaluation.json
```

The evaluator reports absolute and relative error, gate status, interval coverage, and opening detection rate. Missed and phantom openings both count as detection failures.

Useful reproduction commands:

```powershell
python -m unittest discover -s tests -v
.\scripts\run_official_sample.ps1
.\scripts\run_drift_ablation.ps1 -Capture .\single_scan_with_ceiling
```

The current suite contains 12 deterministic tests. The official runner evaluates all three supplied captures through LiDAR, native video, and derived-photo smoke paths; derived photos are not represented as independent photo-tier evidence.

## Reported evidence

- Supplied LiDAR outputs: 40.4456 m2, 98.1217 m2, and 116.1356 m2 footprints; the ceiling-covered capture estimates 2.4247 m height.
- RGB/LiDAR sensor-reference calibration on nine synchronized frames: global scale 0.918525, median absolute relative pixel error 30.555%, and 95th-percentile relative error 179.879%.
- Candidate photo benchmark: 11 available checks, 0% gate pass rate, 100% interval coverage, and 0% opening detection rate. The measured failures are retained in the report rather than hidden.

These supplied-data and candidate results are not substitutes for an independent laser benchmark, repeat capture, or consumer-app comparison.

## Capture and reports

- [Capture protocol](docs/CAPTURE_PROTOCOL.md)
- [Device matrix](docs/DEVICE_MATRIX.md)
- [Compliance matrix](docs/COMPLIANCE.md)
- [Benchmark report](docs/BENCHMARK_REPORT.md)
- [Technical report](docs/TECHNICAL_REPORT.md)
- [Fix-loop declaration](docs/FIX_LOOP.md)
- [Head-to-head template](docs/HEAD_TO_HEAD_TEMPLATE.md)
- [Submission handoff](SUBMISSION.md)

## Repository and private evidence

GitHub intentionally excludes raw captures, residence photos/video, generated runs, private ground truth, model weights, virtual environments, and submission archives. This keeps the repository small and avoids publishing private imagery.

Create the separately shareable evidence package with:

```powershell
.\scripts\build_submission.ps1
```

The script produces a source archive, candidate-evidence archive, complete Git-history bundle, and SHA-256 manifest under `submission/`. Share the evidence privately alongside the GitHub repository; do not force-add ignored datasets or the 216 MB evidence archive to Git.

## Known limitations

- Monocular photo/video scale did not meet the assignment accuracy gates on the available capture.
- Video currently emits one envelope and does not recover a multi-room visual pose graph.
- Photo adjacency can be declared, but physical placement is a non-overlapping ordered layout rather than solved camera geometry.
- LiDAR room boundaries use a Manhattan envelope and clipped Voronoi approximation; concave layouts may be inaccurate.
- Opening and damage logic has synthetic tests but no labelled field precision/recall benchmark.
- The available evidence lacks an independent repeat capture, three complete rooms plus connector, two measured damage classes, and a consumer-app export.

No hosted inference service, private infrastructure, benchmark label, or incumbent-app output is used during inference.
