# =============================================================================
# setup_piper.ps1 — Download Piper TTS binary + en_US-lessac-medium voice
# Run from the PROJECT ROOT: .\setup_piper.ps1
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Paths ─────────────────────────────────────────────────────────────────────
$ProjectRoot = $PSScriptRoot
$BackendDir  = Join-Path $ProjectRoot "backend"
$PiperDir    = Join-Path $BackendDir  "piper"
$VoicesDir   = Join-Path $PiperDir    "voices"
$TempZip     = Join-Path $BackendDir  "piper_windows.zip"

# ── Release info ──────────────────────────────────────────────────────────────
$PiperRelease  = "2023.11.14-2"
$PiperAsset    = "piper_windows_amd64.zip"
$PiperUrl      = "https://github.com/rhasspy/piper/releases/download/$PiperRelease/$PiperAsset"

# Hugging Face direct-download base for en_US-lessac-medium
$HFBase        = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
$OnnxUrl       = "$HFBase/en_US-lessac-medium.onnx"
$JsonUrl       = "$HFBase/en_US-lessac-medium.onnx.json"

# ── Helper ────────────────────────────────────────────────────────────────────
function Write-Step([string]$msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Download-File([string]$url, [string]$dest) {
    Write-Host "    Downloading: $url" -ForegroundColor Gray
    Write-Host "    -> $dest" -ForegroundColor Gray
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
}

# ── 1. Create directories ─────────────────────────────────────────────────────
Write-Step "Creating directories"
New-Item -ItemType Directory -Force -Path $PiperDir  | Out-Null
New-Item -ItemType Directory -Force -Path $VoicesDir | Out-Null
Write-Host "    backend/piper/        OK" -ForegroundColor Green
Write-Host "    backend/piper/voices/ OK" -ForegroundColor Green

# ── 2. Download Piper release zip ─────────────────────────────────────────────
Write-Step "Downloading Piper $PiperRelease (Windows AMD64)"
Download-File $PiperUrl $TempZip

# ── 3. Extract — pull only piper.exe (and any required .dll files) ────────────
Write-Step "Extracting Piper binary"
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($TempZip)

foreach ($entry in $zip.Entries) {
    # The zip places files inside a "piper/" subfolder; flatten into $PiperDir
    $entryName = $entry.Name   # just the filename, no subdirectory prefix

    if ($entryName -eq "") { continue }  # skip directory entries

    $destPath = Join-Path $PiperDir $entryName
    Write-Host "    Extracting: $entryName" -ForegroundColor Gray

    $stream     = $entry.Open()
    $fileStream = [System.IO.File]::Create($destPath)
    $stream.CopyTo($fileStream)
    $fileStream.Close()
    $stream.Close()
}
$zip.Dispose()

# Verify piper.exe exists
$PiperExe = Join-Path $PiperDir "piper.exe"
if (-Not (Test-Path $PiperExe)) {
    Write-Error "piper.exe not found after extraction. Check the zip layout."
    exit 1
}
Write-Host "    piper.exe found at: $PiperExe" -ForegroundColor Green

# ── 4. Download voice model files ─────────────────────────────────────────────
Write-Step "Downloading en_US-lessac-medium voice model"
Download-File $OnnxUrl (Join-Path $VoicesDir "en_US-lessac-medium.onnx")
Download-File $JsonUrl (Join-Path $VoicesDir "en_US-lessac-medium.onnx.json")
Write-Host "    Voice model downloaded successfully." -ForegroundColor Green

# ── 5. Clean up zip ───────────────────────────────────────────────────────────
Write-Step "Cleaning up temporary files"
Remove-Item $TempZip -Force
Write-Host "    Removed: $TempZip" -ForegroundColor Gray

# ── 6. Final layout check ─────────────────────────────────────────────────────
Write-Step "Final layout"
Write-Host ""
Write-Host "  backend/" -ForegroundColor White
Write-Host "  └── piper/" -ForegroundColor White
Write-Host "      ├── piper.exe" -ForegroundColor Green

Get-ChildItem $PiperDir -File | Where-Object { $_.Name -ne "piper.exe" } |
    ForEach-Object { Write-Host "      ├── $($_.Name)" -ForegroundColor Gray }

Write-Host "      └── voices/" -ForegroundColor White
Get-ChildItem $VoicesDir -File |
    ForEach-Object { Write-Host "          ├── $($_.Name)" -ForegroundColor Green }

Write-Host ""
Write-Host "==> Piper TTS setup complete! Start the backend and test Maya." -ForegroundColor Green
