# SpaceScan technical report

## 1. Architecture and contract

The system has one offline entry point and one output schema across three evidence tiers. Ingestion produces tier-specific evidence; geometry produces rooms, surfaces and adjacency; uncertainty wraps every metric value; validation rejects incomplete results; rendering consumes only structured output. This separation makes the SVG auditable and prevents a visually plausible plan from bypassing measurement checks.

The dependency-light implementation is deliberate for a cold walk-in run: NumPy and Pillow are the only Python runtime packages. Results are deterministic for the same bytes and frame budget. Capture IDs hash raw inputs, and diagnostics record frames, point counts, methods, limitations, and runtime.

## 2. Tier design and devices

LiDAR uses uint16 depth (millimetres), confidence maps, per-frame intrinsics, and 6DoF poses. Pixels unproject as `(x, -y, +z)` in Record3D optical coordinates and rotate into ARKit world coordinates. Only high-confidence depth from 0.2–5 m is admitted. Local normals separate horizontal plane evidence from vertical wall evidence.

Video and photos share the output contract but not the evidence strength. The current baseline returns architectural priors with ±25% and ±40% wall intervals respectively. This honestly exposes scale ambiguity but fails the ±3%/±8% gates. The next model path is visual-inertial SfM for video and a disclosed metric-depth/room-layout ensemble for stills, calibrated on held-out properties. The device matrix is in `DEVICE_MATRIX.md`.

## 3. Geometry, stitching, and drift

Floor and ceiling are robust modes of world-height coordinates whose local normals are vertical. A missing ceiling invokes a documented 2.45 m prior and expands the interval from ±2 cm to ±25 cm. Vertical points between planes determine a dominant Manhattan frame; robust projected extrema form the baseline envelope.

For captures that return within 1 m of their origin and span over 2.5 m, an endpoint loop constraint distributes the residual translation along the trajectory before plane anchoring. The ablation command produces plans with this correction on and off. This is a transparent lightweight pose-graph constraint, not a claim of full SLAM re-optimization. Photo folders are laid out without overlap and folder order supplies low-confidence adjacency; this is not yet acceptable whole-property stitching.

## 4. Error budget and calibration

LiDAR wall uncertainty is the larger of 1.5 cm or a term derived from vertical pose variation. Floor-area and surface-area intervals propagate wall/height uncertainty. Ceiling uncertainty is ±2 cm with two observed planes and ±25 cm with the prior. Monocular tiers widen far more. Each interval stores its method, so downstream scope cannot confuse measured and assumed dimensions.

The benchmark evaluator reports absolute error and empirical interval coverage. A nominal 95% system should cover about 95% of held-out ground-truth values; coverage materially below that means overconfidence even if mean error is small. Current constants are engineering priors, not calibrated claims. At least the specified multi-room, damaged, repeated, and cross-tier captures are required before fitting tier-specific residual quantiles.

## 5. Fix loop

The worst observed internal failure was ceiling extraction. A wrong Record3D optical basis dispersed nominally horizontal samples and forced a height prior. Correcting the basis produced sharp floor/ceiling modes and a 2.42 m direct estimate on the supplied ceiling scan. The declaration, prediction, regeneration command, and empty ground-truth cell are in `FIX_LOOP.md`. The cell remains empty because inventing a laser measurement would invalidate the assessment.

## 6. Known failures and next work

The baseline does not yet detect openings, damage, concealed damage, or scope items. It reduces a LiDAR property to one rectangular envelope and cannot represent non-Manhattan/concave rooms. Mirrors, glass, moving objects, low texture, missing ceiling coverage, open doors, and non-closed paths can corrupt evidence. Photo/video results do not meet accuracy gates. These are submission blockers, not footnotes.

Highest-value next work: (1) capture the mandated benchmark and laser truth; (2) split free space into rooms and infer portals jointly; (3) add a disclosed segmentation/detection model for openings and damage, with surface reprojection; (4) implement visual loop closures and pose-graph optimization; (5) calibrate residual intervals per tier; (6) run the same rooms through a named consumer app and fill the head-to-head table.

