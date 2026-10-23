# Smart Document and Finance Analyzer

A local computer-vision project for extracting financial fields and tables, inspecting their source evidence, correcting results, reconciling amounts, and exporting JSON/Excel.

**Team:** Priyanshu Modak (I080), Vishesh Dokania (I019), Parth Zanwar (I074), MPSTME NMIMS.

## Features

- Native PDF text/tables with per-page OCR fallback for scans.
- LayoutLMv3 token inference or a separate document-QA mode, alongside inspectable OCR rules.
- Source-page field highlights, candidate provenance and review flags.
- Invoice arithmetic, GSTIN/PAN/date checks and editable rows.
- Conservative multipage invoice merging and document-level reconciliation.
- Bank transaction review, saved history and nine-sheet Excel export.
- Explicit reviewed-page approval, aligned training export and evaluation-data guards.

## Fresh Windows setup

Install Python 3.11 and Tesseract OCR, then open PowerShell in the cloned repository:

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1 -Mode ocr
```

Open **http://127.0.0.1:8501**. API documentation: http://127.0.0.1:8000/docs.

CPU OCR is the default. Indonesian receipts use bundled neural OCR weights and an included compact classifier; no separate LayoutLM checkpoint download is required. PDFium renders the normal PDF path; Poppler supports the legacy PDF decoder. See [installation details](docs/INSTALLATION.md) for system dependencies and manual environment setup.

Try `sample_docs/demo_digital_invoice.pdf`, then `sample_docs/demo_continued_invoice.pdf`. These are fictional examples, not customer documents. Stop services with `scripts/stop.ps1` before switching modes.

## Source-only repository

Virtual environments, large neural checkpoints, generated/downloaded datasets, document history, uploads, logs, generated reports and release ZIPs stay out of Git. Reviewed fictional demos, three licensed real receipts and the small deployed receipt-classifier JSON are intentionally included.

Generate the training corpus locally on a fresh clone:

```powershell
.\backend\venv\Scripts\python.exe data/build_training_dataset.py --n 1000 --out data/training_indian_invoices --seed 42
.\backend\venv\Scripts\python.exe scripts/validate_dataset.py
```

Use a new output folder if the dataset already exists. The generated split is 700 train / 150 validation / 150 test with exact word boxes and BIO labels. Dataset/model instructions and source licenses are in [data/README_datasets.md](data/README_datasets.md) and [training guide](docs/TRAINING_AND_DATA.md).

Optional GPU setup/training:

```powershell
.\scripts\setup_gpu.ps1
.\scripts\train_gpu.ps1 -Output models/layoutlmv3-new -Epochs 3
```

Large LayoutLMv3 checkpoint weights are not in this repository. The compact Indonesian receipt classifier is included separately under backend/assets. After training or restoring a complete checkpoint, use its relative path explicitly:

```powershell
.\scripts\stop.ps1
.\scripts\start.ps1 -Mode token -ModelPath models/layoutlmv3-new -UseGpu
```

For Docker, copy `.env.example` to `.env` and run `docker compose up --build`. Stop native services first to release the ports.

## Tests and repository audit

```powershell
.\backend\venv\Scripts\python.exe -m unittest discover -s tests -v
.\frontend\venv\Scripts\python.exe -m unittest discover -s frontend/tests -v
.\backend\venv\Scripts\python.exe scripts/audit_repository.py
```

Tests use self-contained fixtures; they do not require the excluded training dataset or model weights. GitHub Actions runs CPU tests and the repository audit on pushes and pull requests. Hosted execution begins after the repository is pushed; local verification is documented separately.

## Results and walkthrough

The [public results summary](docs/results/README.md) records the completed local run and its limitations. Synthetic BIO entity F1, end-to-end field F1, and real-world accuracy are different measurements. OCR rules outperformed the old combined LayoutLM mode on synthetic Indian invoice validation. Indonesian receipt improvements and their separate real-image test results are documented in the Indonesian extraction guide.

- [Full application walkthrough](docs/USER_WALKTHROUGH.md)
- [Professor demonstration and viva](docs/PROFESSOR_DEMO.md)
- [Architecture and API](docs/ARCHITECTURE_AND_API.md)
- [Training, datasets and evaluation](docs/TRAINING_AND_DATA.md)
- [GitHub preparation and push commands](docs/GITHUB_SETUP.md)
- [Third-party notices](NOTICE.md)

The app is intended for trusted local academic use and has no authentication. Permission-cleared real invoice evaluation, trained table structure and robust handwriting/Hindi benchmarks remain future work. Locally generated handbooks, slides and detailed reports can be rebuilt with the supplied scripts; they are not committed automatically.

## Public website and complete walkthrough

Visitors can now try fictional samples inside the app, upload supported documents, inspect evidence, correct fields and download JSON/Excel. The root Docker image runs the website with a private extraction API, isolated visitor histories and public training collection disabled.

Follow the [complete deployment and visitor walkthrough](docs/DEPLOYMENT_WALKTHROUGH.md) for local Docker, Render hosting, expected sample outputs, professor demonstration steps, privacy/storage behavior and the acceptance checklist. A browser is all visitors need once the server is deployed.

## Deploy on Streamlit Community Cloud

Use the root **`streamlit_app.py`** entrypoint with **Python 3.11**. This runs the complete OCR pipeline inside Streamlit, without a separate backend server, GPU or separate LayoutLM checkpoint download. Upload, samples, corrections, revalidation and downloads remain available with isolated visitor histories.

See [exact Streamlit Cloud deployment steps](docs/STREAMLIT_CLOUD.md). Root `requirements.txt`, `packages.txt` and `.streamlit/config.toml` provide the cloud dependencies and five-megabyte upload limit.

## Real receipt datasets and images

The app now includes **Try real receipt images (CORD)** with three licensed real receipt photographs, OCR, published-value comparison and normal review/download controls. A separate 60-image real-data subset has been validated and evaluated, and a small real-data GPU training pilot is complete. Read [real-data setup and honest results](docs/REAL_DATA.md); these Indonesian receipts are a different domain from Indian GST invoices.

## Indonesian receipts

Choose **Bahasa Indonesia receipt (IDR)** for faithful source-language extraction with English/Bahasa field labels. The deployment now includes neural OCR, a classifier trained on 798 unique real receipts, IDR normalization, perspective-aware rows and receipt-specific reconciliation. See [setup, model details and measured accuracy](docs/INDONESIAN_EXTRACTION.md).
