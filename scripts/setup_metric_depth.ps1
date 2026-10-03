param(
    [string]$Python = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ModelRoot = Join-Path $ProjectRoot ".models"
$Repository = Join-Path $ModelRoot "Depth-Anything-V2"
$CheckpointDirectory = Join-Path $ModelRoot "checkpoints"
$Checkpoint = Join-Path $CheckpointDirectory "depth_anything_v2_metric_hypersim_vits.pth"
$CheckpointUrl = "https://huggingface.co/depth-anything/Depth-Anything-V2-Metric-Hypersim-Small/resolve/main/depth_anything_v2_metric_hypersim_vits.pth"
$RepositoryRevision = "a561b849ebae10a6f5ef49e26c83cbbcd36c71bf"
$CheckpointSha256 = "B782898D8A3E8BE1F639DE33837ED85E9B4B73E40F8F5E5CD99067588D722545"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python environment not found at $Python. Create .venv first."
}

New-Item -ItemType Directory -Force -Path $ModelRoot, $CheckpointDirectory | Out-Null

if (-not (Test-Path -LiteralPath (Join-Path $Repository ".git"))) {
    git clone --depth 1 https://github.com/DepthAnything/Depth-Anything-V2.git $Repository
}
$CurrentRevision = git -C $Repository rev-parse HEAD
if ($CurrentRevision.Trim() -ne $RepositoryRevision) {
    git -C $Repository fetch --depth 1 origin $RepositoryRevision
    git -C $Repository checkout --detach $RepositoryRevision
}

& $Python -m pip install --index-url https://download.pytorch.org/whl/cpu `
    "torch==2.7.1" "torchvision==0.22.1"
& $Python -m pip install "opencv-python>=4.10"

if (-not (Test-Path -LiteralPath $Checkpoint)) {
    Invoke-WebRequest -Uri $CheckpointUrl -OutFile $Checkpoint
}
$ActualSha256 = (Get-FileHash -LiteralPath $Checkpoint -Algorithm SHA256).Hash
if ($ActualSha256 -ne $CheckpointSha256) {
    throw "Checkpoint SHA256 mismatch. Expected $CheckpointSha256, got $ActualSha256."
}

& $Python -c "from spacescan.metric_depth import is_available; assert is_available(); print('Metric-depth model is ready.')"
