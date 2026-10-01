# Benchmark report

## Evidence status

The workspace supplied with this implementation contains three Record3D captures but no laser/tape ground truth, opening annotations, damage annotations, same-tier repeat capture declaration, or incumbent-app export. Consequently this report records reproducibility and internal geometry checks only. It does **not** report accuracy gate passes.

| Capture | Frames | Coverage | Result | Approx. cold runtime* |
|---|---:|---|---|---:|
| `single_room/c00a170fe1` | 1,715 | floor, walls; no stable ceiling mode | one envelope + height prior | 5.1 s |
| `single_scan_floor_only/1a8384c3f6` | 5,251 | floor and multi-room-scale trajectory; no ceiling | one envelope + height prior | 5.9 s |
| `single_scan_with_ceiling/c7d28f72c6` | 9,745 | floor, walls, ceiling, closed loop | one envelope + measured plane separation | 6.8 s |

\* Windows host, Python 3.12, 240 uniformly sampled frames; hardware details were not provided. Rerun timing on the submission machine.

## Internal checks

- Corrected optical unprojection produces a sharp floor mode near −1.49 m in the ceiling capture and a ceiling mode near +0.93 m. Their separation is approximately 2.42 m. This is not an accuracy result until compared with a laser measurement.
- The ceiling capture's raw trajectory endpoint error is approximately 0.389 m. The loop-closure ablation changes the rectangular footprint materially, proving that drift handling is active rather than a report-only claim. Whether the constraint improves accuracy requires ground truth.
- All three tiers emit the same keys and measurement interval structure. Unit tests cover quaternion identity, robust plane mode, envelope area, and invalid-contract rejection.

## Required final benchmark runs

| Gate | Photo | Video | LiDAR | Evidence required before submission |
|---|---:|---:|---:|---|
| Wall lengths | ±8% | ±3% | 1 cm or 0.5% repeatability | laser/tape wall IDs |
| Opening width/detection | report | report | ≤2 cm on ≥85% | every real opening + phantom/miss labels |
| Ceiling height | report | report | ≤1.5 cm; repeat spread ≤1 cm | laser height at fixed marked locations |
| Whole-property footprint | ±8% photo | report | report | exterior/room polygon truth |
| Interval calibration | all measurements | all measurements | all measurements | held-out residual coverage |

For each capture, run `spacescan`, then `spacescan-evaluate`. Preserve raw result, evaluation, timing log, and exact Git commit. The evaluator intentionally refuses to manufacture matches for missing room/wall IDs.

## Repeatability table (to fill)

| Room | Tier | Dimension ID | Capture A (m) | Capture B (m) | Spread | Gate | Pass |
|---|---|---|---:|---:|---:|---:|---|
| **pending duplicate capture** | | | | | | max(0.01 m, 0.5%) | |

## Timing table (to fill on clean machine)

| Capture | Tier | Input duration/images | Runtime | Peak RAM | Output hash |
|---|---|---:|---:|---:|---|
| | | | | | |

