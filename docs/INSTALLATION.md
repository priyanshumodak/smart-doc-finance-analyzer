# Installation and operations

## Existing laptop

The project has separate environments: `backend/venv` for the CPU backend, `frontend/venv` for Streamlit and `.gpu-venv` for CUDA training/inference. There is no need to activate an environment when using the supplied commands. Use one backend at a time.

The validation-recommended default is `scripts/start.ps1 -Mode ocr`. For a separate trained-model demonstration use `scripts/start.ps1 -Mode token -UseGpu` after model selection. Stop with `scripts/stop.ps1`. Both bind to localhost. Open http://127.0.0.1:8501. The startup script refuses occupied ports instead of starting a second server.

## Fresh Windows installation

1. Extract the source ZIP to a writable directory. Keep the directory structure.
2. Install Python 3.11 with the launcher available. The supplied setup script invokes `python3.11`; if your installation only exposes `py -3.11`, create the environments with the equivalent commands below.
3. Install Tesseract OCR. `backend/ocr_engine.py` checks PATH and `C:\Program Files\Tesseract-OCR\tesseract.exe`; alternatively set `TESSERACT_CMD`.
4. Install Poppler and expose `pdfinfo` and `pdftoppm` on PATH for the legacy `load_pages` PDF decoder. The normal new PDF path renders through PDFium.
5. Open PowerShell in the extracted root. Run `scripts/setup.ps1`.
6. Start OCR mode and make a demo upload. No model download is required for this mode.
7. If you need token inference, copy your complete trained model directory under `models/` or train a model. Model weights are excluded from the source ZIP.
8. For NVIDIA GPU use, run `scripts/setup_gpu.ps1`, then verify CUDA before using `-UseGpu`.

Equivalent environment creation if needed:

```powershell
py -3.11 -m venv backend/venv
py -3.11 -m venv frontend/venv
.\backend\venv\Scripts\python.exe -m pip install -r backend/requirements.txt -r notebooks/requirements.txt -r tests/requirements.txt
.\frontend\venv\Scripts\python.exe -m pip install -r frontend/requirements.txt
```

External system dependencies and hosted Colab are not bundled or silently installed by these commands.

## Configuration

`.env.example` documents settings; Docker Compose reads `.env`. The Windows launch scripts do not automatically load `.env`. Set environment variables in the same PowerShell before launching if needed.

| Setting | Meaning |
|---|---|
| `OCR_LANGUAGES` | Requested Tesseract language packs, default `eng+hin`; available requested packs are used |
| `TESSERACT_CMD` | Explicit OCR executable path |
| `TOKEN_MIN_CONFIDENCE` | Token-field acceptance threshold, default 0.5 |
| `INFERENCE_DEVICE` | `auto`, `cpu` or `cuda`; auto chooses CUDA only when the selected environment supports it |
| `TEXT_EXTRACTION_MODE` | `auto` for native PDF text with OCR fallback; `ocr` forces OCR |
| `MAX_UPLOAD_MB` / `MAX_PAGES` | Default 20 MB / 20 pages per document |
| `DATABASE_PATH` | SQLite location; previews are stored alongside it |
| `BACKEND_URL` | Dashboard API URL; launch script sets localhost |

Example:

```powershell
$env:OCR_LANGUAGES='eng'
.\scripts\start.ps1 -Mode ocr
```

`auto` mode uses the separate pretrained invoice QA model and may download it; it does not mean the locally fine-tuned token model. `token` mode supplies the trained checkpoint and keeps inspected OCR fallbacks. The optional learned spatial candidate scorer is detected from `models/spatial-relations.json`.

## Files to preserve

| Location | Contents |
|---|---|
| `models/` | Trained weights, processor, metadata and metrics |
| `storage/documents.sqlite3` | Extracted results, originals of corrected values and review approvals |
| `storage/previews/` | Processed page images used for highlights and approved annotation export |
| `run/preferred_model.json` | Validation-selected checkpoint |
| `reports/` | Measured tests, benchmarks and evaluations |

Raw source uploads are not retained by the app. Processed previews, extracted financial text and annotations are retained locally. Keep the database and its previews together in a private backup. The source archive excludes them by default. The app is designed for a trusted local academic demonstration and has no authentication.

## Logs and troubleshooting

- `run/backend-error.log`, `run/backend.log`: API startup, extraction and model diagnostics.
- `run/frontend-error.log`, `run/frontend.log`: dashboard logs.
- `run/upgrade-finish.log`, `run/upgrade-finish-error.log`: automatic training-completion workflow.
- `reports/test_logs/`: exact regression output.

| Symptom | Action |
|---|---|
| Browser cannot connect | Check both health endpoints and service logs; start services from the root |
| Port 8000 or 8501 in use | Stop this app with its stop script; inspect other programs before stopping anything else |
| OCR unavailable | Check Tesseract path and `tesseract --list-langs`; use `TESSERACT_CMD` if needed |
| Hindi requested but missing | Install the `hin` trained-data language pack; English-only availability does not prove Hindi support |
| Model unavailable | Inspect logs; use OCR mode or provide a complete checkpoint with processor files |
| CUDA unavailable | Use the GPU environment and verify driver/Torch compatibility, or use CPU mode |
| GPU out of memory | Use batch size 1; avoid concurrent GPU training and model inference; keep encoder checkpointing enabled |
| 503 another document processing | Retry after the active request; the pipeline intentionally serializes extraction |
| Preview absent on an old saved result | Re-upload the source to generate a current preview and summary |
| Wrong or empty table | Inspect source quality and headers, correct the rows and retain the review flag where unresolved |
| Insufficient data | Supply or correct missing values; this status does not mean arithmetic passed |
| Training interrupted | Follow the checkpoint resume instructions; do not overwrite the baseline |

## Docker option

`docker compose up --build` is supplied but requires Docker Desktop/engine and local ports to be free. Stop native services first. The container images install English/Hindi Tesseract and Poppler. The model mount is read-only; document history uses a named volume. Set `EXTRACTION_MODE=ocr` in `.env` for a model-free start. Docker GPU passthrough is not configured here. Local Windows verification does not imply Docker execution was tested on this laptop.

## Regenerate the handbook and slides

```powershell
.\backend\venv\Scripts\python.exe -m pip install -r scripts/requirements_docs.txt
.\backend\venv\Scripts\python.exe scripts/project_status.py --write
.\backend\venv\Scripts\python.exe scripts/build_upgrade_report.py
.\backend\venv\Scripts\python.exe scripts/build_handbook.py
```

The handbook builder also refreshes the editable presentation and its PDF when the documentation dependencies are installed. These dependencies are separate from the runtime app. Temporary system wakefulness was requested only while the unattended completion worker runs; it does not change permanent Windows power settings or keep the display on.


Recovery note: the first unattended completion attempt stopped after successful training/baseline evaluation because its Windows-written policy JSON had an encoding marker. The reader now accepts UTF-8 with or without that marker. The resumed job reuses completed evaluation, and its log/error files are `run/upgrade-finish-resume.log` and `run/upgrade-finish-resume-error.log`. `run/upgrade_completion.json` is the current workflow state; older log files are retained as history.


The initial live CUDA first-upload crash was resolved by initializing model libraries in the server startup lifecycle before requests enter the worker pool. A subsequent real HTTP upload verified model layoutlmv3-gpu-v2 on cuda:0 with 14 accepted model fields. The final app uses OCR mode because its validation field quality is higher; see `reports/live_model_verification.json` for the separate model integration result.


Final successful documentation and packaging output is captured in `run/upgrade-finalization.log`. Earlier attempt logs retain their original errors as history. `run/upgrade_completion.json`, `docs/STATUS.md` and final live-verification reports identify the completed working configuration.
