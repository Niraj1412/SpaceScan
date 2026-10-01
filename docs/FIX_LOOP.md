# Fix-loop declaration

## Declaration

Worst observed internal gate: **ceiling-height extraction on the supplied ceiling capture**. Before the fix, the plane selector failed to find a plausible floor/ceiling pair and fell back to the 2.45 m prior, so it could not qualify for the ≤1.5 cm measured gate.

Root-cause hypothesis: Record3D exports optical coordinates as `(image_x, -image_y, +depth)`. The original unprojection treated the recorded landscape orientation as an axis permutation. Evidence: under the old basis, “horizontal” points were spread broadly; under the corrected basis the floor forms a sharp mode around −1.49 m and the ceiling a sharp mode around +0.93 m across independently sampled frames.

Shipped fix: `src/spacescan/lidar.py` now uses the validated optical basis before applying the ARKit quaternion. On the supplied capture, it estimates a 2.42 m floor-to-ceiling separation from two planes instead of returning the residential prior.

Prediction: **after a laser value is added, absolute height error will be ≤3 cm**. This is intentionally not a claim that the 1.5 cm gate passes. The prediction must be replaced with the declared number before looking at the measurement; then the post-mortem records the result.

## Regeneration

After run:

```powershell
spacescan single_scan_with_ceiling --output runs/fix_after
```

Before run: check out the commit immediately before the `Record3D optical basis` fix into a separate worktree, run the same command, and save it under `runs/fix_before`. Do not overwrite either result. The readable diff is the coordinate-basis hunk in `src/spacescan/lidar.py` plus `evaluation.json` from both directories.

## Fill after measurement

| Item | Before | Predicted after | Actual after |
|---|---:|---:|---:|
| Ceiling height absolute error | prior-dependent / unscored | ≤0.030 m | **[measure]** |
| Gate ≤0.015 m | fail | not claimed | **[pass/fail]** |

Post-mortem: **[Was the prediction correct? What residual error came from depth noise, plane support, pose alignment, or ground-truth endpoint choice?]**

