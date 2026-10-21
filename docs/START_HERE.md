# Start here: complete project handover

This folder explains how to run, use, train, evaluate and demonstrate Smart Document and Finance Analyzer. When returning from AFK, read the generated `docs/RETURN_FROM_AFK.md` (generated locally). Read the automatically generated `docs/STATUS.md` (generated locally) for actual completion and measurements; instructions below do not imply a pending training run is finished.

## 1. Open the project

Open PowerShell and run:

```powershell
Set-Location -LiteralPath 'C:\Users\Priyam\Downloads\smart-doc-finance-analyzer'
```

Open http://127.0.0.1:8501. The API documentation is http://127.0.0.1:8000/docs.

If the app is already running, use it. Avoid restarting during the automatic completion job: it switches to the selected model after training. Check:

```powershell
Get-Content run/upgrade_completion.json
Get-Content run/upgrade-finish.log -Tail 20
```

A completion status of `running` means work is still in progress; `complete` means training, comparisons, deployment and packaging finished; `failed` contains an error to investigate. A process ID by itself is not proof it is still alive.

## 2. Start after a Windows restart

The preferred trained model is recorded in `run/preferred_model.json`, and the recommended operating mode in `run/preferred_mode.json`. Validation favors OCR rules for final-field quality, so start the main demonstration with:

```powershell
.\scripts\start.ps1 -Mode ocr
```

Optional trained-model demonstration (stop existing services first):

```powershell
.\scripts\start.ps1 -Mode token -UseGpu
```

CPU model inference:

```powershell
.\scripts\start.ps1 -Mode token
```

OCR-only fallback, including a fresh source-only installation:

```powershell
.\scripts\start.ps1 -Mode ocr
```

Before switching modes, stop the current services:

```powershell
.\scripts\stop.ps1
```

If local script execution is blocked, use a process-scoped invocation for the trusted script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Mode ocr
```

## 3. First successful extraction

1. Upload `sample_docs/demo_digital_invoice.pdf`.
2. Click **Analyze documents** and wait for the result.
3. Check the text-source label, selected page and extracted values.
4. Choose **Highlight a field** to see its evidence on the page.
5. Inspect validation checks and review reasons. Missing evidence is not a passed check.
6. Correct errors, click **Save corrections and revalidate**, then export JSON or Excel.

The sidebar's **Highlight confidence below** control changes visual review emphasis. It does not change the model's acceptance threshold or retrain the model.

## 4. Read the guides in order

| Guide | What it covers |
|---|---|
| [Installation and operations](INSTALLATION.md) | Existing laptop, new computer, configuration, logs, restart and troubleshooting |
| [User walkthrough](USER_WALKTHROUGH.md) | Upload, evidence, multipage results, correction, approvals and export |
| [Datasets and training](TRAINING_AND_DATA.md) | Corpus provenance, annotation, GPU training, resume, evaluation and model selection |
| [Architecture and API](ARCHITECTURE_AND_API.md) | How the pipeline works, code map, request/response examples |
| [Professor demonstration and viva](PROFESSOR_DEMO.md) | Timed demonstration, explanation, questions and defensible claims |
| [Change log](CHANGELOG.md) | Implemented improvements, verification and remaining work |
| `docs/STATUS.md` (generated locally) | Generated from actual artifacts rather than manually copied scores |

`artifacts/PROJECT_HANDBOOK.pdf` is the printable handbook. `artifacts/PROFESSOR_PRESENTATION.pptx` is the editable slide deck with speaker notes; a matching presentation PDF is also provided. `artifacts/finance-analyzer.zip` contains source, public data and documentation; installed environments, model weights and private review/history are excluded. The working laptop retains its trained weights under `models/`.

After live verification, `artifacts/DEMO_OUTPUT.xlsx` and `artifacts/DEMO_OUTPUT.json` provide a saved generated-invoice extraction example. The final model archive has a SHA-256 sidecar and per-file manifest. Recreate outputs by uploading the supplied demo sources, rather than treating example outputs as unseen accuracy evidence.

## 5. Verify before presenting

```powershell
.\backend\venv\Scripts\python.exe scripts/project_status.py
.\backend\venv\Scripts\python.exe scripts/verify_live_app.py
.\backend\venv\Scripts\python.exe scripts/verify_upgraded_app.py
```

The first command reports saved state and service health without starting training. The next two make real demo uploads and create saved history records. For regression tests, run `scripts/verify_tests.py` with the backend Python. Read `reports/UPGRADE_RESULTS.md` for measured results and their scope.

## Deploy a website visitors can use

Read the [full public deployment walkthrough](DEPLOYMENT_WALKTHROUGH.md). It covers one-click samples, visitor uploads, expected outputs, corrections, Excel downloads, Render hosting and a two-browser acceptance check.
