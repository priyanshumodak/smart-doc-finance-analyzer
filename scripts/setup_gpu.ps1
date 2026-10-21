$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
& backend/venv/Scripts/python.exe -m venv .gpu-venv
& .gpu-venv/Scripts/python.exe -m pip install --no-deps torch==2.3.1 --index-url https://download.pytorch.org/whl/cu121
if ($LASTEXITCODE -ne 0) { throw 'CUDA PyTorch installation failed' }
& .gpu-venv/Scripts/python.exe -m pip install -r backend/requirements.txt -r notebooks/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'GPU environment dependencies failed' }
& .gpu-venv/Scripts/python.exe -c "import torch; print(torch.__version__); assert torch.cuda.is_available(), 'CUDA unavailable; check NVIDIA driver'; print(torch.cuda.get_device_name(0))"
if ($LASTEXITCODE -ne 0) { throw 'GPU verification failed' }
