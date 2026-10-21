param([string]$Output='models/layoutlmv3-gpu-v2',[int]$Epochs=3,[double]$TargetValidationF1=0.99)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$pythonPath=Join-Path $projectRoot '.gpu-venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run scripts/setup_gpu.ps1 first' }
& $pythonPath -c "import torch; assert torch.cuda.is_available(), 'CUDA unavailable'; print(torch.cuda.get_device_name(0))"
if ($LASTEXITCODE -ne 0) { throw 'CUDA verification failed' }
if (Test-Path -LiteralPath (Join-Path $Output 'config.json')) { throw 'Output already contains a model. Choose another -Output directory.' }
$env:HF_HUB_DISABLE_XET='1'
$env:OMP_NUM_THREADS='4'
$env:MKL_NUM_THREADS='4'
$baseModel=if (Test-Path -LiteralPath 'models/layoutlmv3-indian-invoices/config.json') { 'models/layoutlmv3-indian-invoices' } else { 'microsoft/layoutlmv3-base' }
& $pythonPath -u notebooks/finetune_layoutlmv3.py --data_dir data/training_indian_invoices --model_name $baseModel --output_dir $Output --epochs $Epochs --batch_size 1 --max_length 256 --gradient_checkpointing --cpu_threads 4 --target_validation_f1 $TargetValidationF1
if ($LASTEXITCODE -ne 0) { throw 'Training failed; inspect the reported error before retrying' }
