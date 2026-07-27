# reorganize_piper.ps1
# Runs after re-extraction to put espeak-ng-data in its own directory
# so piper's espeak-ng doesn't accidentally parse our ONNX voice models.

$PiperDir    = "d:\LJ_Projects\Sem6\Project Maya\backend\piper"
$TempSrc     = "$env:TEMP\piper_reextract\piper"
$EspeakDir   = "$PiperDir\espeak-ng-data"

Write-Host "Setting up proper espeak-ng-data directory..." -ForegroundColor Cyan

# Create espeak-ng-data directory (proper isolated location for espeak's data)
New-Item -ItemType Directory -Force -Path $EspeakDir | Out-Null

# Copy espeak-ng-data from the properly structured zip extraction
# The zip has: piper/espeak-ng-data/ with its own voices/ subdirectory inside
Copy-Item "$TempSrc\espeak-ng-data\*" -Destination $EspeakDir -Recurse -Force

Write-Host "espeak-ng-data/ structure:" -ForegroundColor Cyan
Get-ChildItem $EspeakDir | Select-Object Name, Length | Format-Table

# Cleanup temp files
Remove-Item "$env:TEMP\piper_reextract" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$env:TEMP\piper_reextract.zip" -Force -ErrorAction SilentlyContinue

Write-Host "Done. ESPEAK_DATA_PATH should point to: $EspeakDir" -ForegroundColor Green
