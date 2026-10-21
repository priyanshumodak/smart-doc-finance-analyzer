param([switch]$Resume)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$workerLock=[System.IO.File]::Open((Join-Path $projectRoot 'run\upgrade-worker.lock'),[System.IO.FileMode]::OpenOrCreate,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None)
$startedAt=(Get-Date).ToString('o')
function Save-Stage([string]$Stage,[string]$Status='running',[string]$Message='') {
    @{status=$Status;stage=$Stage;process_id=$PID;started_at=$startedAt;updated_at=(Get-Date).ToString('o');message=$Message} | ConvertTo-Json | Set-Content run/upgrade_completion.json
    Write-Output "[$((Get-Date).ToString('o'))] $Stage $Status $Message"
}
function Invoke-Checked([string]$Python,[string[]]$Arguments) {
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Failed: $Python $Arguments" }
}
try {
    Save-Stage 'waiting_for_training'
    while ($true) {
        $workers=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*python*' -and $_.CommandLine -like '*finetune_layoutlmv3.py*--output_dir models/layoutlmv3-gpu-v2*' })
        if (-not (Test-Path models/layoutlmv3-gpu-v2/config.json)) {
            & $PSScriptRoot/finalize_if_target_met.ps1
        }
        if ((Test-Path models/layoutlmv3-gpu-v2/test_results.json) -and $workers.Count -eq 0) { break }
        if ($workers.Count -eq 0 -and -not (Test-Path models/layoutlmv3-gpu-v2/test_results.json)) { throw 'Training stopped without final test metrics; inspect training logs.' }
        Start-Sleep -Seconds 30
    }
    Save-Stage 'baseline_full_evaluation'
    if ($Resume -and (Test-Path reports/baseline_full_evaluation/validation_results.json) -and (Test-Path reports/baseline_full_evaluation/test_results.json)) {
        Write-Output 'Reusing completed full-split baseline evaluation; selection validates matching split sizes.'
    } else {
    Invoke-Checked '.gpu-venv/Scripts/python.exe' @('-u','notebooks/finetune_layoutlmv3.py','--data_dir','data/training_indian_invoices','--model_name','models/layoutlmv3-indian-invoices','--output_dir','reports/baseline_full_evaluation','--evaluate_only','--max_length','256','--batch_size','1','--cpu_threads','4')
    }
    Save-Stage 'validation_only_selection'
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/complete_training_metadata.py')
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/select_model.py','--candidate','models/layoutlmv3-gpu-v2')
    Save-Stage 'same_document_comparison'
    foreach ($mode in @('model','token')) {
        Invoke-Checked '.gpu-venv/Scripts/python.exe' @('-u','scripts/benchmark_pipeline.py','--mode',$mode,'--model','models/layoutlmv3-gpu-v2','--offset','20','--limit','10','--out',"reports/v2_comparison/$mode")
    }
    Invoke-Checked '.gpu-venv/Scripts/python.exe' @('scripts/compare_modes.py','--model','models/layoutlmv3-gpu-v2','--offset','20','--limit','10','--out','reports/v2_comparison','--reuse')
    Save-Stage 'external_synthetic_validation'
    Invoke-Checked '.gpu-venv/Scripts/python.exe' @('-u','scripts/benchmark_pipeline.py','--data','data/kirana_external','--split','validation','--limit','5','--mode','token','--model','models/layoutlmv3-gpu-v2','--out','reports/external_kirana_token')
    Save-Stage 'regression_verification'
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/verify_tests.py')
    Save-Stage 'deploy_and_verify'
    & $PSScriptRoot/stop.ps1
    $deployMode=if (Test-Path run/preferred_mode.json) { (Get-Content run/preferred_mode.json -Raw | ConvertFrom-Json).recommended_mode } else { 'ocr' }
    if ($deployMode -eq 'token') { & $PSScriptRoot/start.ps1 -Mode token -UseGpu } else { & $PSScriptRoot/start.ps1 -Mode ocr }
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/verify_live_app.py')
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/verify_upgraded_app.py')
    Save-Stage 'model_package'
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/package_model.py')
    Save-Stage 'reports_and_documentation'
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/build_upgrade_report.py')
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/project_status.py','--write')
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/build_handbook.py')
    Save-Stage 'source_package'
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/package_project.py','--dataset')
    Save-Stage 'finished' 'complete' 'Training, evaluations, tests, live verification, model/source packages and handbook finished.'
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/project_status.py','--write')
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/build_handbook.py')
    Invoke-Checked 'backend/venv/Scripts/python.exe' @('scripts/package_project.py','--dataset')
} catch {
    Save-Stage 'error' 'failed' $_.Exception.Message
    throw
} finally { $workerLock.Dispose() }
