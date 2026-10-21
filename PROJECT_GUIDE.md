# Complete project guide

The current step-by-step instructions are organized in [docs/START_HERE.md](docs/START_HERE.md). Read `docs/STATUS.md` (generated locally) before claiming training or deployment is complete.

1. [Install and run](docs/INSTALLATION.md).
2. [Upload, inspect evidence, correct and export](docs/USER_WALKTHROUGH.md).
3. [Prepare data, train, resume and evaluate](docs/TRAINING_AND_DATA.md).
4. [Understand architecture and use the API](docs/ARCHITECTURE_AND_API.md).
5. [Demonstrate to the professor and prepare viva answers](docs/PROFESSOR_DEMO.md).
6. [Review all implementation changes](docs/CHANGELOG.md).
7. [Read measured upgrade results](docs/results/README.md).

## Quick start on this laptop

```powershell
Set-Location -LiteralPath 'C:\Users\Priyam\Downloads\smart-doc-finance-analyzer'
.\scripts\start.ps1 -Mode ocr
```

Dashboard: http://127.0.0.1:8501. API: http://127.0.0.1:8000/docs.

If already running, open the existing dashboard. Before switching modes, run `scripts/stop.ps1`. Use `-Mode ocr` without GPU or model weights; use `-Mode token` for CPU inference. Do not start duplicate training/completion workers.

## Printable and transferable artifacts

- `artifacts/PROJECT_HANDBOOK.pdf`: maintained guides and measured results in one PDF.
- `artifacts/finance-analyzer.zip`: source, public data and documentation; no installed environments/private history/model weights.
- `artifacts/finance-analyzer-model.zip`: selected inference model, generated after successful completion.

The source-only project can run OCR mode immediately after dependency/system setup. To restore token mode, extract the separate model archive into the same project root, preserving its `models/` directory.

## Historical baseline

The initial CPU integration model remains in `models/layoutlmv3-indian-invoices`. It trained for 60 optimizer steps using a capped 140-example training subset and 20-example validation/test subsets. Historical entity F1 was 0.415 validation and 0.444 test. Those values are not directly comparable with larger evaluation subsets. The new report includes a matched full-split reevaluation when completed.

An earlier guide described only CPU installation and 17 backend/two dashboard checks. Those were historical snapshots. Current setup includes a separate CUDA environment; current test counts come from `reports/upgraded_tests.json` and the generated status page. Source-supported feature details remain in [UPGRADE_GUIDE.md](UPGRADE_GUIDE.md).


Validation recommends OCR rules for final-field extraction quality. The trained token model remains available with `scripts/start.ps1 -Mode token -UseGpu`, and its live CUDA inference is recorded separately. Higher BIO entity F1 does not imply the combined pipeline beats the rule mode. See `reports/validation_modes/selection.json` and the final upgrade report.
