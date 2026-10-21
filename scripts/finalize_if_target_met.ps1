$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$outputPath=Join-Path $projectRoot 'models\layoutlmv3-gpu-v2'
if (Test-Path -LiteralPath (Join-Path $outputPath 'config.json')) { Write-Output 'Model already finalized; wait for its evaluation results.'; exit }
$policy=Get-Content -LiteralPath 'run\training_policy.json' -Raw | ConvertFrom-Json
$qualified=$null
$checkpoints=Get-ChildItem -LiteralPath $outputPath -Directory -Filter 'checkpoint-*' | Sort-Object LastWriteTime -Descending
foreach ($checkpoint in $checkpoints) {
    $statePath=Join-Path $checkpoint.FullName 'trainer_state.json'
    $weightsPath=Join-Path $checkpoint.FullName 'model.safetensors'
    if ((Test-Path -LiteralPath $statePath) -and (Test-Path -LiteralPath $weightsPath)) {
        $state=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        if ($state.best_metric -ge $policy.target_validation_f1) { $qualified=$checkpoint; break }
    }
}
if (-not $qualified) { Write-Output 'No complete checkpoint has reached the declared validation target yet.'; exit }
# Validate the completed safetensors header before stopping only this project's job.
& .gpu-venv/Scripts/python.exe -c "from safetensors import safe_open; import sys; f=safe_open(sys.argv[1],framework='pt',device='cpu'); assert len(list(f.keys()))>0" (Join-Path $qualified.FullName 'model.safetensors')
if ($LASTEXITCODE -ne 0) { throw 'Checkpoint validation failed; training left running' }
$workers=Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*finetune_layoutlmv3.py*--output_dir models/layoutlmv3-gpu-v2*' }
function Stop-TrainingTree([int]$ProcessId) {
    foreach ($child in (Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue)) {
        Stop-TrainingTree -ProcessId $child.ProcessId
    }
    Stop-Process -Id $ProcessId -ErrorAction SilentlyContinue
}
foreach ($worker in $workers) { Stop-TrainingTree -ProcessId $worker.ProcessId }
& .gpu-venv/Scripts/python.exe -u scripts/finalize_checkpoint.py --checkpoint $qualified.FullName --output models/layoutlmv3-gpu-v2 --target $policy.target_validation_f1
if ($LASTEXITCODE -ne 0) { throw 'Checkpoint finalization failed; original checkpoint remains available' }
& .gpu-venv/Scripts/python.exe -u notebooks/finetune_layoutlmv3.py --data_dir data/training_indian_invoices --model_name models/layoutlmv3-gpu-v2 --output_dir reports/gpu_v2_evaluation --evaluate_only --max_length 256 --cpu_threads 4
if ($LASTEXITCODE -ne 0) { throw 'Final model evaluation failed' }
Copy-Item -LiteralPath reports/gpu_v2_evaluation/validation_results.json -Destination models/layoutlmv3-gpu-v2/validation_results.json
Copy-Item -LiteralPath reports/gpu_v2_evaluation/test_results.json -Destination models/layoutlmv3-gpu-v2/test_results.json
Write-Output 'Validation-target checkpoint finalized and evaluated.'
