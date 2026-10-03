param(
  [string]$Output = "runs/official_sample"
)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path "$PSScriptRoot/.."
$env:PYTHONPATH = "$repo/src"
$datasets = @("single_room", "single_scan_floor_only", "single_scan_with_ceiling")
$rows = @()

$metricDepthAvailable = python -c "from spacescan.metric_depth import is_available; print('yes' if is_available() else 'no')"
if ($metricDepthAvailable.Trim() -eq "yes") {
  $calibrationOutput = Join-Path $repo "$Output/depth_calibration.json"
  python -m spacescan.depth_calibration `
    (Join-Path $repo "single_room") `
    (Join-Path $repo "single_scan_floor_only") `
    (Join-Path $repo "single_scan_with_ceiling") `
    --frames 4 --output $calibrationOutput --write-calibration
} else {
  Write-Warning "Optional metric-depth bundle is unavailable; photo/video rows will use architectural priors."
}

foreach ($dataset in $datasets) {
  $captureRoot = Join-Path $repo $dataset
  $scan = Get-ChildItem -LiteralPath $captureRoot -Directory | Select-Object -First 1
  if (-not $scan) { throw "No raw scan folder found under $captureRoot" }
  $video = Join-Path $scan.FullName "rgb.mp4"
  if (-not (Test-Path -LiteralPath $video)) { throw "Missing $video" }

  $photoRoom = Join-Path $repo "sample_inputs/photos/$dataset"
  New-Item -ItemType Directory -Force -Path $photoRoom | Out-Null
  $durationText = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $video
  $duration = [double]::Parse($durationText.Trim(), [Globalization.CultureInfo]::InvariantCulture)
  $sampleFps = 8.0 / $duration
  $fpsText = $sampleFps.ToString("0.########", [Globalization.CultureInfo]::InvariantCulture)
  & ffmpeg -y -loglevel error -i $video -vf "fps=$fpsText" -frames:v 8 (Join-Path $photoRoom "frame_%02d.jpg")

  $targets = @(
    @{ Tier = "lidar"; Input = $captureRoot },
    @{ Tier = "video"; Input = $video },
    @{ Tier = "photos-derived"; Input = $photoRoom }
  )
  foreach ($target in $targets) {
    $resultDir = Join-Path $repo "$Output/$dataset/$($target.Tier)"
    python -m spacescan.cli $target.Input --output $resultDir
    $resultPath = Join-Path $resultDir "result.json"
    $result = Get-Content -Raw $resultPath | ConvertFrom-Json
    $rows += [pscustomobject]@{
      dataset = $dataset
      requested_tier = $target.Tier
      output_tier = $result.capture.tier
      capture_id = $result.capture.id
      rooms = @($result.property.rooms).Count
      footprint_m2 = $result.property.footprint_area.value
      ceiling_m = $result.property.rooms[0].ceiling_height.value
      runtime_seconds = $result.diagnostics.runtime_seconds
      result = $resultPath
    }
  }
}

$summaryPath = Join-Path $repo "$Output/summary.json"
$rows | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $summaryPath
$rows | Format-Table dataset,requested_tier,rooms,footprint_m2,ceiling_m,runtime_seconds -AutoSize
Write-Host "Official sample matrix written to $summaryPath"
Write-Warning "The photos-derived rows are video-frame smoke tests, not independent photo-tier benchmark captures."
