# Device and accuracy matrix

These are claims for the current baseline, not aspirational gates. Replace benchmark columns only after blind laser/tape evaluation.

| Hardware | Photos | Video | LiDAR | Baseline 95% wall interval | Expected gate status |
|---|---:|---:|---:|---:|---|
| iPhone 15 / 15 Plus | Yes | Yes | No | photo ±40%; video ±25% | Fails metric gates until monocular model is shipped |
| iPhone 15 Pro / Pro Max | Yes | Yes | Yes | LiDAR ≥±1.5 cm plus pose term | Needs benchmark; does not claim 0.5% gate yet |
| Newer non-Pro iPhone without LiDAR | Yes | Yes | No | same as photo/video | Same degraded path |
| Newer Pro-class iPhone with LiDAR | Yes | Yes | Yes | same LiDAR path; device must be benchmarked | Unverified until added to matrix |

Ceiling intervals are ±2 cm when both horizontal planes are observed and ±25 cm when a 2.45 m residential prior is required. Photo/video ceiling intervals are ±45 cm/±30 cm. The output states the method for every measurement.

The capture protocol deliberately separates capability from phone generation: the application detects available artifacts, not a marketing model name.

