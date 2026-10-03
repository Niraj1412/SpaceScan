# SpaceScan technical report

## 1. Architecture and contract

The system has one offline entry point and one output schema across photos, video, and LiDAR. Tier-specific ingestion feeds geometry and inspection; uncertainty wraps every metric value; validation rejects incomplete results; rendering consumes only structured output. This keeps the SVG auditable and prevents a visually plausible plan from bypassing measurement checks.

The base package requires NumPy and Pillow. The optional photo/video bundle adds CPU PyTorch, torchvision, OpenCV, and the official Depth Anything V2 Small indoor metric checkpoint. It is installed by `scripts/setup_metric_depth.ps1` and runs locally. Results are deterministic for the same bytes, weights, calibration, and frame budget. Capture IDs hash raw inputs; diagnostics record evidence, methods, limitations, and runtime.

## 2. Tier design

LiDAR uses uint16 millimetre depth, confidence maps, per-frame intrinsics, and 6DoF poses. Pixels unproject in the validated Record3D optical basis and rotate into ARKit world coordinates. Only high-confidence depth from 0.2-5 m is admitted. Local normals separate horizontal planes from vertical wall evidence.

For photos and video, the optional model predicts dense indoor range for sampled RGB frames. Robust far range and lateral point-cloud span form a rectangular room hypothesis. Without the model, an explicit architectural-prior fallback remains available. This is not structure-from-motion: unknown camera poses prevent rigorous stitching, so this path does not claim the assignment's +/-3% or +/-8% gates.

## 3. Geometry, stitching, and drift

Floor and ceiling are robust modes of world-height coordinates whose local normals are vertical. A missing ceiling invokes a documented 2.45 m prior with a much wider interval. Vertical points determine a dominant Manhattan frame; robust projected extrema form the property envelope. Property-scale trajectories are deterministically clustered; clipped Voronoi cells partition that envelope without overlap, while temporal transitions produce adjacency evidence. Conservative wall-height histograms emit a door only when a lower/middle gap has lintel support.

For a path that returns within 1 m of its origin and spans over 2.5 m, an endpoint constraint distributes horizontal residual translation along the trajectory before plane anchoring. The ablation command produces correction-on and correction-off plans. This is a transparent lightweight constraint, not full SLAM re-optimization.

## 4. Error budget and calibration

LiDAR wall uncertainty is the larger of 1.5 cm or a term derived from pose variation. Floor and surface intervals propagate wall and height uncertainty. Ceiling uncertainty is +/-2 cm with two observed planes and +/-25 cm with the prior.

The metric-depth checkpoint was checked on nine synchronized frames across all three supplied captures. One median scale of 0.918525 gave 30.555% median absolute relative pixel error and a 179.879% 95th-percentile tail. Because the reference is supplied iPhone LiDAR rather than laser truth, the full broad residual is propagated; it is not a gate pass. Held-out properties and laser measurements remain necessary for defensible calibration.

The evaluator reports absolute error, relative error, per-measurement gate status, and interval coverage. A nominal 95% interval should cover roughly 95% of held-out truth; materially lower coverage means overconfidence even if mean error is small.

## 5. Inspection and scope

Strongly supported LiDAR wall gaps can become openings. Repeated centred colour anomalies can become disclosed mold-like or water-stain-like regions. Accepted damage creates evidence-linked concealed-moisture flags and surface-keyed scope quantities. These are triage signals, not material diagnoses. Synthetic tests exercise the safeguards; labelled field precision/recall is still unavailable.

## 6. Fix loop and known failures

The worst observed internal failure was ceiling extraction. An incorrect optical basis dispersed horizontal samples and forced a height prior. Correcting the basis produced sharp plane modes and a 2.42 m direct estimate on the supplied ceiling scan. `FIX_LOOP.md` records the declaration and regeneration command; the laser-truth cell remains blank rather than fabricated.

Voronoi room boundaries can differ from physical walls, the envelope cannot represent a concave exterior, and photo/video room geometry can vary substantially with viewpoint. Mirrors, glass, motion, low texture, open doors, and non-closed paths can corrupt evidence. Highest-value next work is independent capture plus laser truth, labelled openings/damage, full visual pose estimation, and a same-room consumer-app comparison.
