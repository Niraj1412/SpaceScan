# Compliance matrix

Legend: **done** is executable now; **partial** is present but does not meet the stated accuracy/product gate; **blocked** needs new capture/measurement evidence; **missing** has not been built.

| Requirement | File path | Artifact | Status |
|---|---|---|---|
| Stock capture route | `docs/CAPTURE_PROTOCOL.md` | One-page operator instructions | done |
| Device matrix | `docs/DEVICE_MATRIX.md` | Hardware/tier/accuracy table | done |
| One command per capture | `src/spacescan/cli.py` | `spacescan INPUT -o OUTPUT` | done |
| Photos accepted | `src/spacescan/media.py`, `metric_depth.py` | Folder ingestion, local metric-depth aggregation, calibrated wide intervals | partial: no multi-view poses or blind accuracy pass |
| Video accepted | `src/spacescan/media.py`, `metric_depth.py` | Clip sampling, local metric-depth aggregation, calibrated wide intervals | partial: no visual pose graph or blind accuracy pass |
| LiDAR depth/poses/intrinsics | `src/spacescan/lidar.py` | Metric point cloud and planes | done |
| Per-room walls, height, area | `src/spacescan/models.py`, `lidar.py` | Interval-valued JSON | partial: rectangular envelope only |
| Openings and detection scoring | `inspection.py`, output `rooms[].openings` | Conservative LiDAR wall-gap detector | partial: synthetic-tested; blind miss/phantom rate unmeasured |
| Multi-room stitched plan | `lidar.py`, `geometry.py`, `media.py`, `render.py` | Non-overlapping trajectory/Voronoi rooms and adjacency | partial: implemented; doorway correctness needs ground truth |
| Damage class + metric extent | `inspection.py`, output `rooms[].damages` | Repeated centered colour-anomaly regions | partial: synthetic-tested; benchmark classes unmeasured |
| Concealed-damage flags | `inspection.py`, output `concealed_damage_flags` | Evidence-linked moisture rules | done |
| Scope line items keyed to surfaces | `inspection.py`, output `scope_line_items` | Surface/damage-linked quantities | done |
| Confidence interval every measurement | `models.py`, validator | value/low/high/unit/confidence/method | done |
| Published JSON schema | `schema/output.schema.json` | Draft 2020-12 nested contract | done |
| Rendered plan | `src/spacescan/render.py` | SVG with dimensions/intervals | done |
| Drift correction + ablation | `lidar.py`, `scripts/run_drift_ablation.ps1` | Endpoint constraint on/off outputs | done; benefit must be measured |
| Repeatability gate | `spacescan-evaluate` + duplicate captures | Per-dimension errors | blocked: duplicate capture/ground truth needed |
| Three-tier benchmark | `benchmark/ground_truth.example.json` | Deterministic evaluator | blocked: required benchmark capture not supplied |
| RGB-depth model calibration | `depth_calibration.py`, `runs/depth_calibration.json` | Nine synchronized frames; global scale and residuals | done as sensor-reference check; not laser truth |
| Benchmark report | `docs/BENCHMARK_REPORT.md` | Reproducibility checks + required tables | partial: accuracy rows blocked by missing truth |
| Head-to-head vs consumer app | `docs/HEAD_TO_HEAD_TEMPLATE.md` | Dimension table template | blocked: same-room app export needed |
| Fix loop before/after | `docs/FIX_LOOP.md` | Declaration and commands | partial: code fix shipped; laser result pending |
| Raw benchmark evidence | external reproduction bundle | Original files/checksums | blocked: candidate must capture and upload |

This matrix intentionally does not convert “field exists” into “requirement passed.”
