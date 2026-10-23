# Deploy the complete app on Streamlit Community Cloud

This deployment runs everything inside one Streamlit application. It directly reuses the extraction, OCR, correction, reconciliation, storage and export functions. There is no separate FastAPI server, Render service, Docker installation, separate LayoutLM download or API key required. Compact neural OCR models arrive with the pinned package installation. FastAPI remains an installed Python dependency because the shared functions use its validation/response types; no HTTP server is started.

## 1. Push the Streamlit deployment changes

From the repository root:

```powershell
git status
git push origin main
```

The deployment commit includes these files:

| File | Purpose |
|---|---|
| `streamlit_app.py` at the repository root | Cloud entrypoint; enables standalone public OCR mode |
| `requirements.txt` at the root | Installs OCR/backend libraries plus the Streamlit UI |
| `packages.txt` | Installs Tesseract, Hindi OCR language data and Poppler |
| `.streamlit/config.toml` | Five-megabyte uploader limit and Streamlit settings |
| `backend/standalone.py` | Calls shared pipeline functions directly with visitor ownership checks |

Do not select `frontend/streamlit_app.py` in Community Cloud. That path is the original HTTP-backed interface and has its own frontend-only requirements. The root entrypoint selects the complete root requirements and standalone processing.

## 2. Create the hosted app

1. Open https://share.streamlit.io/ and sign in with GitHub.
2. Click **Create app** and choose the option to deploy from GitHub.
3. Select these exact values:

   | Setting | Value |
   |---|---|
   | Repository | `priyanshumodak/smart-doc-finance-analyzer` |
   | Branch | `main` |
   | Main file path | `streamlit_app.py` |
   | Python version, under Advanced settings | **3.11** |

4. Choose an available app URL if the form offers a subdomain field. No secrets are required. Do not add `BACKEND_URL`, model paths or API tokens.
5. Click **Deploy**. The host installs Python requirements and Linux packages, then launches the app. Watch its build logs if installation fails.
6. Once it opens, use the sample workflow below. Share the resulting `https://...streamlit.app` URL with your professor after the acceptance check.

Select Python 3.11 explicitly: the project's pinned NumPy/Pandas/Streamlit versions were tested with that interpreter. `.python-version` is useful locally but does not replace the Community Cloud deployment form's Python selection.

Official instructions: [deploy an app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [Python and Linux dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), [file organization](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization).

## 3. Demonstrate the working website

1. Open **Start here: a complete walkthrough**.
2. Under **Try a sample without uploading a file**, select **Digital invoice (fastest)**, then **Analyze this sample**. This runs real extraction, not a stored answer. Expected subtotal: **100**, tax: **18**, total: **118**.
3. Select a field under **Highlight a field** and compare its location with the extracted value. Explain that a digital PDF can use embedded text; a scanned image uses Tesseract OCR.
4. Change total to **130**, click **Save corrections and revalidate**, and inspect the amount mismatch. Restore **118** and save again. The existing default amount tolerance is one currency unit, so a one-unit change may still pass.
5. Click **Download JSON**, then **Prepare Excel download** and **Download Excel**. Open the workbook and show its fields, table rows and validation sheets.
6. Analyze **Continued invoice (two pages)** and inspect page switching and combined rows. Expect total **354** and two merged rows.
7. Analyze **Scanned invoice (OCR)**, **Bank statement**, and **Financial report** to show the other paths. Check outputs against the source; unfamiliar layouts can require manual correction.
8. Download a sample, select it through **Upload PDF, image or multipage TIFF**, then click **Analyze documents**. This demonstrates the visitor upload flow.
9. Open an incognito window. The first window's saved results must not appear there.
10. Click **Clear my documents** in the first window. Verify that its saved records disappear. Clearing results does not delete files already downloaded to your computer.

The longer [visitor walkthrough](DEPLOYMENT_WALKTHROUGH.md) explains the source evidence, document types and limitations. Use this document's deployment steps for Streamlit Cloud; the other guide's Docker/Render steps are an alternative hosting path.

## 4. Limits, storage and expectations

- This Cloud entrypoint forces public OCR mode and disables training collection. No GPU or paid AI API is required.
- Each file is limited to **5 MB**, **three pages**, and **10 million decoded pixels per image**. These conservative bounds reduce memory pressure; they do not guarantee every scan fits the host's available resources.
- One extraction runs at a time. Another visitor may receive a busy message and should retry after it finishes.
- History belongs to the current Streamlit session, not an account. Download outputs before leaving. Refresh, reconnection or restart may lose the session.
- Extracted results and raster previews are saved in temporary server storage. Closing a tab does not delete them. Use **Clear my documents**; orphaned records persist until storage is reset. There is no automatic retention timer.
- The filesystem is not durable storage. The host can restart, sleep or replace the app, and stored results can disappear. Use fictional or redacted documents for a public academic demonstration.
- Recognition, layout heuristics and arithmetic checks have limits. A passed check does not guarantee accurate extraction. Demonstrate review and correction rather than claiming every uploaded document will work perfectly.

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| Backend unavailable / connection refused | Confirm **Main file path = `streamlit_app.py`** at the repository root. The standalone entrypoint makes no backend HTTP calls. |
| Missing backend module or OCR package | Ensure the root `requirements.txt`, `backend/requirements-ocr.txt` and `packages.txt` are pushed. Reboot/redeploy after dependency changes. |
| NumPy/Pandas install error on a newer Python | Redeploy with Python **3.11** selected under Advanced settings. |
| Tesseract not found | Check installation logs for root `packages.txt`; it must include `tesseract-ocr`. |
| PDF cannot be decoded | Try the included digital PDF first. Check Poppler installation, remove passwords and stay under page limits. |
| App runs out of memory | Try a one-page, lower-resolution file. Avoid processing batches during a live demonstration. Restart the app from the owner controls if needed. |
| Server busy | Wait for the current extraction to finish and retry. |
| History disappeared | Reupload or use the downloaded JSON/Excel. Session history is temporary. |

## 6. Run this exact mode locally

Use Python 3.11, install `requirements.txt`, and install Tesseract and Poppler as described in [installation](INSTALLATION.md). Then run:

```powershell
python -m streamlit run streamlit_app.py
```

Do not start the separate backend for this mode. The existing `scripts/start.ps1` still starts the alternative HTTP-backed local app.

## Local verification

The updated project passes 66 regressions: 59 backend/data tests, four HTTP-backed dashboard tests and three rendered Cloud entrypoint tests. The real-receipt test checks the actual neural engine and the known real-image total, while prohibiting external API calls. It also verifies that reference labels never enter extraction.

The root Python environment uses no Torch or Transformers at inference; `pip check` passes. RapidOCR and ONNX Runtime are pinned to tested CPU versions. The live site is https://smart-doc-finance-analyzer-p5ekraetyvhbhjr5o2ween.streamlit.app/ . Latest model, evaluation scope and deployment checks are documented in [the Indonesian receipt guide](INDONESIAN_EXTRACTION.md).

## Local 500 error after updating

If you kept the older two-service app running during an update, its backend can still have the old storage code in memory. The error `table documents has 6 columns but 5 values were supplied` identifies that stale process. Stop it with `powershell -ExecutionPolicy Bypass -File scripts/stop.ps1`, then restart the current app. Do not delete the database to fix this.

For a fresh local Streamlit-only environment, run from the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Tesseract and Poppler must also be installed locally; `packages.txt` installs them automatically only on Community Cloud. Existing Windows setup is covered in the installation guide. Open http://localhost:8501 after starting.

**Review required** is a status, not a button. Analyze or open a document first, then find **Review and correct** beside its source preview (scroll further down on narrow screens). Double-click the **value** cells to edit, check item rows, and click **Save corrections and revalidate** at the bottom of the form. You may save an unchanged form to record that you checked it; unresolved mismatches still require review.

## Indonesian receipt profile

After deploying the latest main branch, select **Bahasa Indonesia receipt (IDR)** for receipt photos. English/Bahasa field labels, original source text and normalized IDR values are supported. CPU neural OCR packages and a small trained classifier are included; no paid API or GPU is required. See [the Indonesian receipt guide](INDONESIAN_EXTRACTION.md).
