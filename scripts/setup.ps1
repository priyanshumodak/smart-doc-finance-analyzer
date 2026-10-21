$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$launcher=$null
$launcherArgs=@()
if (Get-Command python3.11 -ErrorAction SilentlyContinue) { $launcher='python3.11' }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $launcher='py'; $launcherArgs=@('-3.11') }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $launcher='python' }
else { throw 'Install Python 3.11 and expose python3.11, py -3.11, or python on PATH.' }
& $launcher @launcherArgs -c "import sys; assert sys.version_info[:2]==(3,11), 'This project requires Python 3.11'"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 verification failed' }
foreach ($environmentPath in @('backend/venv','frontend/venv')) {
    if (-not (Test-Path -LiteralPath (Join-Path $environmentPath 'Scripts/python.exe'))) {
        & $launcher @launcherArgs -m venv $environmentPath
        if ($LASTEXITCODE -ne 0) { throw "Environment creation failed: $environmentPath" }
    }
}
& backend/venv/Scripts/python.exe -m pip install -r backend/requirements.txt -r notebooks/requirements.txt -r tests/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed' }
& frontend/venv/Scripts/python.exe -m pip install -r frontend/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed' }
Write-Output 'Setup complete. Start with scripts/start.ps1 -Mode ocr.'
