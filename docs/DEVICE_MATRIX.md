# Device and accuracy matrix

These are claims for the current baseline, not aspirational gates. Replace benchmark columns only after blind laser/tape evaluation.

| Hardware | Photos | Video | LiDAR | Current 95% interval | Expected gate status |
|---|---:|---:|---:|---:|---|
| iPhone 15 / 15 Plus | Yes | Yes | No | residual-based; current proxy is up to +/-180% | Model ships locally; accuracy gate remains unverified and proxy error is high |
| iPhone 15 Pro / Pro Max | Yes | Yes | Yes | LiDAR >= +/-3 cm plus pose/loop term | Needs laser benchmark; does not claim 0.5% gate |
| Newer non-Pro iPhone without LiDAR | Yes | Yes | No | same photo/video path | Same model-backed degraded path |
| Newer Pro-class iPhone with LiDAR | Yes | Yes | Yes | same LiDAR path | Device must be benchmarked before adding an accuracy claim |

Ceiling intervals are +/-2 cm when both horizontal planes are observed and +/-25 cm when a 2.45 m residential prior is required. Photo/video ceiling intervals are +/-45 cm and +/-30 cm. Every output measurement states its method.

The optional photo/video model is Depth Anything V2 Metric Indoor Small. It runs on CPU after `scripts/setup_metric_depth.ps1`; without it, the program falls back to clearly labelled architectural priors. The capture protocol separates capability from phone generation: the application detects available artifacts, not a marketing model name.
