# Benchmark report

## Evidence status

The supplied workspace contains three Record3D captures but no laser/tape ground truth, opening labels, damage labels, declared repeat capture, or consumer-app export. Therefore this report documents reproducibility and sensor-reference checks only. It does not report accuracy-gate passes.

| Capture | Frames | LiDAR output | Latest runtime |
|---|---:|---|---:|
| `single_room/c00a170fe1` | 1,715 | 1 room, 40.4456 m2, height prior | 1.030 s |
| `single_scan_floor_only/1a8384c3f6` | 5,251 | 4 rooms, 98.1217 m2, height prior | 1.128 s |
| `single_scan_with_ceiling/c7d28f72c6` | 9,745 | 4 rooms, 116.1356 m2, 2.4247 m measured height | 1.203 s |

Windows host, Python 3.12, 240 uniformly sampled LiDAR frames. Runtime varies by hardware.

## Internal checks

- Corrected optical unprojection produces a floor mode near -1.49 m and ceiling mode near +0.93 m in the ceiling capture, a separation near 2.42 m. This is not an accuracy result without laser comparison.
- Raw endpoint error for that capture is about 0.389 m. The correction ablation materially changes the footprint, showing that drift handling is active; ground truth is needed to prove improvement.
- All tiers emit the same schema and interval structure. Ten unit tests cover geometry, partitioning, detection safeguards, metric-depth aggregation, tier inference, and contract validation.

## Model-backed RGB sensor-reference check

Depth Anything V2 Metric Indoor Small was run on nine synchronized frames spanning all supplied captures. Against valid high-confidence iPhone LiDAR pixels, the global scale was 0.918525, median absolute relative error 0.30555, and 95th-percentile relative error 1.79879. `runs/depth_calibration.json` records per-frame evidence. This is a sensor-reference diagnostic, not laser truth.

After calibration, the three video footprint outputs were 15.0048, 28.7854, and 32.6038 m2. The corresponding eight-frame photo smoke tests were 14.4519, 21.0204, and 78.7090 m2. Their disagreement with LiDAR is disclosed as a failure signal rather than hidden or averaged away. Derived photos test the interface and are not independent captures.

## Candidate-captured RGB evidence

On 4 October 2026, the candidate captured 18 original Android photographs and one 39.14-second 3840x2160 walkthrough of a quarter-type residence. The prepared photo input contains an entrance, a 2.00 x 0.90 m corridor, and a 3.20 x 2.90 m bedroom. Both measured spaces have a 2.40 m ceiling; the entrance door measures 0.80 x 1.90 m.

The photo evaluation scored eleven available checks: pass rate 0.0, mean numeric absolute error 5.1648 m, interval coverage 1.0, and opening detection rate 0.0. The 3.20 x 2.90 m bedroom was predicted as 5.9371 x 7.8457 m (85.53% and 170.54% errors); corridor dimensions were worse. The video path produced a single 5.4971 x 6.0517 m envelope and cannot semantically separate the room from its connector. These are documented failures of monocular geometry and stitching, not accuracy claims.

## Required final benchmark gates

| Gate | Photo | Video | LiDAR | Evidence still required |
|---|---:|---:|---:|---|
| Wall lengths | +/-8% | +/-3% | 1 cm or 0.5% repeatability | laser/tape wall IDs |
| Opening width/detection | report | report | <=2 cm on >=85% | all real openings plus phantom/miss labels |
| Ceiling height | report | report | <=1.5 cm; repeat spread <=1 cm | laser height at marked locations |
| Whole-property footprint | +/-8% | report | report | exterior/room polygon truth |
| Interval calibration | all | all | all | held-out residual coverage |

For each independently captured property, run `spacescan`, then `spacescan-evaluate`. Preserve the raw result, evaluation, timing, exact commit, and measurement sketch. The evaluator refuses to manufacture matches for missing IDs.

## Repeatability placeholder

| Room | Tier | Dimension ID | Capture A | Capture B | Spread | Gate | Pass |
|---|---|---|---:|---:|---:|---:|---|
| **pending duplicate capture** | | | | | | max(0.01 m, 0.5%) | |
