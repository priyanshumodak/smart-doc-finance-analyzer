param([ValidateSet('ocr','auto','token')][string]$Mode='ocr',[string]$ModelPath='',[switch]$UseGpu)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$runDir=Join-Path $projectRoot 'run'
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$backendPython=Join-Path $projectRoot 'backend\venv\Scripts\python.exe'
if ($UseGpu) { $backendPython=Join-Path $projectRoot '.gpu-venv\Scripts\python.exe' }
$frontendPython=Join-Path $projectRoot 'frontend\venv\Scripts\python.exe'
foreach ($pythonPath in @($backendPython,$frontendPython)) {
    if (-not (Test-Path -LiteralPath $pythonPath)) { throw "Missing environment: $pythonPath. Run scripts/setup.ps1 first." }
}
foreach ($port in @(8000,8501)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Port $port is in use. Check the running application before starting another instance." }
}
$env:EXTRACTION_MODE=if ($Mode -eq 'ocr') {'ocr'} else {'auto'}
$env:TOKEN_MODEL_PATH=''
if ($Mode -eq 'token') {
    if (-not $ModelPath) {
        $preferred=Join-Path $projectRoot 'run\preferred_model.json'
        $ModelPath=if (Test-Path -LiteralPath $preferred) { (Get-Content -LiteralPath $preferred -Raw | ConvertFrom-Json).model_path } else { 'models/layoutlmv3-indian-invoices' }
    }
    $resolvedModel=Join-Path $projectRoot $ModelPath
    if (-not (Test-Path -LiteralPath (Join-Path $resolvedModel 'config.json'))) { throw "No trained model at $resolvedModel" }
    $env:TOKEN_MODEL_PATH=$resolvedModel
}
$env:RELATION_MODEL_PATH=''
if (Test-Path -LiteralPath (Join-Path $projectRoot 'models/spatial-relations.json')) { $env:RELATION_MODEL_PATH=Join-Path $projectRoot 'models/spatial-relations.json' }
$env:BACKEND_URL='http://127.0.0.1:8000'
$env:OMP_NUM_THREADS='4'
$env:MKL_NUM_THREADS='4'
$backend=Start-Process -FilePath $backendPython -ArgumentList @('-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runDir 'backend.log') -RedirectStandardError (Join-Path $runDir 'backend-error.log') -PassThru
$frontend=Start-Process -FilePath $frontendPython -ArgumentList @('-m','streamlit','run','frontend/streamlit_app.py','--server.address=127.0.0.1','--server.port=8501','--server.headless=true','--browser.gatherUsageStats=false') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runDir 'frontend.log') -RedirectStandardError (Join-Path $runDir 'frontend-error.log') -PassThru
@{backend=$backend.Id;frontend=$frontend.Id;mode=$Mode;use_gpu=$UseGpu.IsPresent;started_at=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runDir 'services.json')
Write-Output "Backend PID: $($backend.Id); frontend PID: $($frontend.Id)"
Write-Output 'Dashboard: http://127.0.0.1:8501'
Write-Output 'API: http://127.0.0.1:8000/docs'
Write-Output "Logs: $runDir"
