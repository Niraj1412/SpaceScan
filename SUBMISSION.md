# Submission handoff

## Upload files

Run:

```powershell
.\scripts\build_submission.ps1
```

Upload the three generated artifacts plus `SHA256SUMS.txt` from `submission/`:

- `spacescan-source.zip`: committed source, schema, tests, scripts, and reports.
- `spacescan-candidate-evidence.zip`: original candidate photos/video, capture manifest, ground truth, generated JSON/SVG results, evaluations, calibration, and timing evidence.
- `spacescan-history.bundle`: complete Git history for process-evidence review. A reviewer can inspect it with `git clone spacescan-history.bundle spacescan-history`.

The optional model checkout, checkpoint, and virtual environment are deliberately excluded. `scripts/setup_metric_depth.ps1` fetches the pinned model revision and checksum-verified weights. The company-supplied LiDAR data is omitted from the default archive because the reviewer already owns it; use `-IncludeSuppliedLidar` if a self-contained large bundle is required.

## Final verification

```powershell
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
.\scripts\run_official_sample.ps1
spacescan .\property_photos --output .\runs\own_photos
spacescan '.\property_photos\05_full video\VID_20261003_223333956.mp4' --output .\runs\own_video
spacescan-evaluate .\runs\own_photos\result.json .\benchmark\my_ground_truth.json --output .\runs\own_photos\evaluation.json
```

## Disclosure

This is a functional but partially compliant submission. The available benchmark lacks an independent repeat capture, three complete rooms plus connector, two measured damage classes, and a consumer-app export. Candidate RGB accuracy gates fail and the report states the measured failures. No missing result is fabricated.
