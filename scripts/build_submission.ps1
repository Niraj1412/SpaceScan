param(
  [string]$Output = "submission",
  [switch]$IncludeSuppliedLidar
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot/..").Path
$destination = Join-Path $repo $Output
New-Item -ItemType Directory -Force -Path $destination | Out-Null

$sourceZip = Join-Path $destination "spacescan-source.zip"
$evidenceZip = Join-Path $destination "spacescan-candidate-evidence.zip"
foreach ($archive in @($sourceZip, $evidenceZip)) {
  if (Test-Path -LiteralPath $archive) {
    Remove-Item -LiteralPath $archive -Force
  }
}

git -C $repo archive --format=zip --output $sourceZip HEAD

$evidence = @(
  (Join-Path $repo "property_photos"),
  (Join-Path $repo "benchmark"),
  (Join-Path $repo "runs")
)
if ($IncludeSuppliedLidar) {
  $evidence += @(
    (Join-Path $repo "single_room"),
    (Join-Path $repo "single_scan_floor_only"),
    (Join-Path $repo "single_scan_with_ceiling")
  )
}
$missing = @($evidence | Where-Object { -not (Test-Path -LiteralPath $_) })
if ($missing.Count) {
  throw "Missing evidence paths: $($missing -join ', ')"
}
Compress-Archive -LiteralPath $evidence -DestinationPath $evidenceZip -CompressionLevel Optimal

$hashes = foreach ($archive in @($sourceZip, $evidenceZip)) {
  $hash = Get-FileHash -LiteralPath $archive -Algorithm SHA256
  "$($hash.Hash.ToLowerInvariant())  $([IO.Path]::GetFileName($archive))"
}
$hashes | Set-Content -LiteralPath (Join-Path $destination "SHA256SUMS.txt") -Encoding ascii

Get-Item -LiteralPath $sourceZip, $evidenceZip | Select-Object Name, Length, LastWriteTime
Write-Host "Submission files written to $destination"
if (-not $IncludeSuppliedLidar) {
  Write-Warning "Company-supplied LiDAR folders are omitted by default; reviewers can use the original sample-data link. Pass -IncludeSuppliedLidar to bundle them."
}
