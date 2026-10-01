# Compliance matrix

Legend: **done** is executable now; **partial** is present but does not meet the stated accuracy/product gate; **blocked** needs new capture/measurement evidence; **missing** has not been built.

| Requirement | File path | Artifact | Status |
|---|---|---|---|
| Stock capture route | `docs/CAPTURE_PROTOCOL.md` | One-page operator instructions | done |
| Device matrix | `docs/DEVICE_MATRIX.md` | Hardware/tier/accuracy table | done |
| One command per capture | `src/spacescan/cli.py` | `spacescan INPUT -o OUTPUT` | done |
| Photos accepted | `src/spacescan/media.py` | Folder ingestion, room layout, wide intervals | partial |
| Video accepted | `src/spacescan/media.py` | Clip ingestion, metadata, wide intervals | partial |
| LiDAR depth/poses/intrinsics | `src/spacescan/lidar.py` | Metric point cloud and planes | done |
| Per-room walls, height, area | `src/spacescan/models.py`, `lidar.py` | Interval-valued JSON | partial: rectangular envelope only |
| Openings and detection scoring | output `rooms[].openings` | Published field | missing detector |
| Multi-room stitched plan | `media.py`, `render.py` | Non-overlapping SVG and adjacency list | partial: folder-order fallback; no LiDAR room split |
| Damage class + metric extent | output `rooms[].damages` | Published field | missing detector |
| Concealed-damage flags | output `concealed_damage_flags` | Published field | missing rules |
| Scope line items keyed to surfaces | output `scope_line_items` | Published field | missing rules/catalogue |
| Confidence interval every measurement | `models.py`, validator | value/low/high/unit/confidence/method | done |
| Published JSON schema | `schema/output.schema.json` | Draft 2020-12 schema | partial: top-level strictness only |
| Rendered plan | `src/spacescan/render.py` | SVG with dimensions/intervals | done |
| Drift correction + ablation | `lidar.py`, `scripts/run_drift_ablation.ps1` | Endpoint constraint on/off outputs | done; benefit must be measured |
| Repeatability gate | `spacescan-evaluate` + duplicate captures | Per-dimension errors | blocked: duplicate capture/ground truth needed |
| Three-tier benchmark | `benchmark/ground_truth.example.json` | Deterministic evaluator | blocked: required benchmark capture not supplied |
| Benchmark report | `docs/BENCHMARK_REPORT.md` | Reproducibility checks + required tables | partial: accuracy rows blocked by missing truth |
| Head-to-head vs consumer app | `docs/HEAD_TO_HEAD_TEMPLATE.md` | Dimension table template | blocked: same-room app export needed |
| Fix loop before/after | `docs/FIX_LOOP.md` | Declaration and commands | partial: code fix shipped; laser result pending |
| Raw benchmark evidence | external reproduction bundle | Original files/checksums | blocked: candidate must capture and upload |

This matrix intentionally does not convert “field exists” into “requirement passed.”
