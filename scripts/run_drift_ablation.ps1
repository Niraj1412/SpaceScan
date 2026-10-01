param(
  [Parameter(Mandatory=$true)][string]$Capture,
  [string]$Output = "runs/drift_ablation"
)
$ErrorActionPreference = "Stop"
$env:PYTHONPATH = (Resolve-Path "$PSScriptRoot/../src")
python -m spacescan.cli $Capture --output "$Output/on"
python -m spacescan.cli $Capture --output "$Output/off" --no-drift-correction
Write-Host "Ablation written to $Output/on and $Output/off"
