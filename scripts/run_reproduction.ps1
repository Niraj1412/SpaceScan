param(
  [string]$PhotoCapture = "test_photos",
  [string]$VideoCapture = "single_room/c00a170fe1/rgb.mp4",
  [string]$LidarCapture = "single_scan_with_ceiling",
  [string]$Output = "runs/reproduction"
)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path "$PSScriptRoot/.."
$env:PYTHONPATH = "$repo/src"

python -m unittest discover -s "$repo/tests" -v
python -m spacescan.cli "$repo/$PhotoCapture" --output "$repo/$Output/photos"
python -m spacescan.cli "$repo/$VideoCapture" --output "$repo/$Output/video"
python -m spacescan.cli "$repo/$LidarCapture" --output "$repo/$Output/lidar"

$summary = @()
foreach ($tier in @("photos", "video", "lidar")) {
  $resultPath = "$repo/$Output/$tier/result.json"
  $result = Get-Content -Raw $resultPath | ConvertFrom-Json
  $openingCount = ($result.property.rooms | ForEach-Object { @($_.openings).Count } | Measure-Object -Sum).Sum
  $damageCount = ($result.property.rooms | ForEach-Object { @($_.damages).Count } | Measure-Object -Sum).Sum
  $summary += [pscustomobject]@{
    tier = $tier
    capture_id = $result.capture.id
    rooms = $result.property.rooms.Count
    openings = $openingCount
    damages = $damageCount
    runtime_seconds = $result.diagnostics.runtime_seconds
    result = $resultPath
  }
}
$summary | ConvertTo-Json | Set-Content -Encoding UTF8 "$repo/$Output/summary.json"
$summary | Format-Table -AutoSize
Write-Host "Reproduction bundle written to $repo/$Output"
