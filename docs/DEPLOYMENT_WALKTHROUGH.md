# Deploy Finance Document Studio and demonstrate it

This guide deploys the complete Python application: a Streamlit website, an internal FastAPI extraction service, Tesseract OCR, PDF support and fictional demonstration files. Visitors need only a browser; they do not install Python, train a model or supply an API key. The public container uses the measured recommended OCR mode and does not download neural model weights.

## 1. Try the complete workflow locally

For the existing Windows installation:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1 -Mode ocr
```

Open http://127.0.0.1:8501. If it is already running, stop it with `scripts/stop.ps1` before restarting to load backend changes. New installations should first follow [installation](INSTALLATION.md).

1. Expand **Start here: a complete walkthrough**.
2. Under **Try a sample without uploading a file**, select **Digital invoice (fastest)** and click **Analyze this sample**. This runs the actual extraction pipeline, not a precomputed result.
3. Expect invoice `DEMO-DIGITAL-2026`, subtotal **100**, tax **18**, total **118** and one item. Check the source preview against the extracted values.
4. Use **Highlight a field** to see its evidence on the page. Expand OCR text or extraction provenance for inspection. Digital PDF text can bypass OCR; image scans run OCR.
5. In the correction form, change total to `119`, then **Save corrections and revalidate**. The amount mismatch should require review. Restore `118` and save again. Inspect the validation checks rather than treating the status as an accuracy guarantee.
6. Click **Download JSON**. Click **Prepare Excel download**, then **Download Excel**. The workbook contains Fields, Line Items, Validation, Provenance, Transactions, Financial Metrics, Spatial Relations, Document Summary and Merged Line Items sheets.
7. Try **Continued invoice (two pages)**: switch between pages and expand combined results. Expect two merged item rows and total **354**.
8. Try the scanned invoice to demonstrate OCR, the bank statement for transaction/balance checks, and the financial report for metrics. Recognition and supported fields vary by document; review uncertain results.
9. To upload your own file, choose a PDF, PNG, JPEG or TIFF and click **Analyze documents**. Multiple uploads run sequentially. Clear, upright scans work best. Use fictional or redacted files for public demonstrations.
10. Reopen results from sidebar history. In public mode, **Clear my documents** deletes the session's extracted records, previews and any associated training reviews. Downloads already saved to your device remain on your device.

## 2. Test the public container

Install and start Docker Desktop with Linux containers, then run from the repository root:

```powershell
docker build -t finance-document-studio .
docker run --rm --name finance-document-studio -p 8501:8501 finance-document-studio
```

Open http://localhost:8501. Stop with Ctrl+C, or `docker stop finance-document-studio` in another terminal. The root `Dockerfile` is the public deployment; the older two-service `docker-compose.yml` remains a local development setup with a directly exposed API. Use the root Dockerfile for this guide.

Only the website port is published. FastAPI listens on loopback port 8000 inside the container. The launcher waits for OCR/API readiness before starting Streamlit, supervises both processes and stops the container if either process exits. Keep one container instance for this demonstration: SQLite, previews and sessions are local to that instance.

The root image installs `backend/requirements-ocr.txt`, not PyTorch or Transformers. Local model training and GPU inference continue to use the existing full requirements and separate setup. Rebuild the image after changes to dependencies or samples.

## 3. Push the source to GitHub

Follow [GitHub setup](GITHUB_SETUP.md). Commit the deployment changes and push `main` to your repository. Do not upload local environments, models, uploads, extracted records or private documents. These are excluded by `.gitignore`; the container context has its own `.dockerignore`.

GitHub Pages cannot run this Python application. Use a Docker web-service host.

## 4. Deploy on Render

The repository includes `render.yaml`, or you can create the service manually:

1. Sign in to Render and connect your GitHub repository.
2. Choose **New > Web Service**, select the repository and choose the **Docker** runtime. Use the repository root as the build context and `./Dockerfile` as the Dockerfile path. Leave the Docker command override empty.
3. Alternatively choose **New > Blueprint** and select the repository; review the `render.yaml` service before creating it.
4. Select an instance size and review the current price before creating the service. Start with roughly **2 GB RAM** as a practical initial allocation for OCR/PDF work, then measure actual memory under representative uploads. This is a sizing suggestion, not a benchmark or performance guarantee. Small free instances may exhaust memory on large scans.
5. Keep `PUBLIC_DEMO_MODE=1`, `EXTRACTION_MODE=ocr`, `MAX_UPLOAD_MB=10` and `MAX_PAGES=5`. The Dockerfile supplies these defaults; the Blueprint also makes the limits explicit. Do not configure a GPU or model download for the first deployment.
6. Set health-check path to `/_stcore/health`. The launcher reads the host-provided `PORT` and binds Streamlit to `0.0.0.0`. Do not set `BACKEND_URL` to a visitor's localhost or expose port 8000.
7. Deploy, watch build/startup logs and wait for the service to become healthy. Open the provided HTTPS URL and complete the acceptance checks below before sharing it.
8. Share that HTTPS URL with your professor or visitors. They can try samples or upload a supported document immediately.

By default the database and page previews live in `/tmp/finance-demo` on ephemeral container storage. They can disappear on replacement/redeploy. A plain process restart may retain files on the same filesystem; there is no promise of deletion when a tab closes. If persistent storage is later added, explicitly plan retention and backups and change the in-app privacy description accordingly.

Official platform references: [Render Docker deployment](https://render.com/docs/docker), [web services and ports](https://render.com/docs/web-services), [Blueprint reference](https://render.com/docs/blueprint-spec), [health checks](https://render.com/docs/health-checks), and [Streamlit Docker deployment](https://docs.streamlit.io/deploy/tutorials/docker). Check the host's current plans and UI at deployment time.

## 5. Public acceptance checklist

- Open the HTTPS URL in a normal browser and a separate incognito window.
- In the first window analyze the digital sample; confirm the expected totals, source preview and downloads.
- Confirm its filename is absent from the second window's history. Analyze another sample there and verify both sessions work independently.
- In the first window edit a value, save and inspect revalidation. Reopen it from history and verify the correction remains.
- Download the sample, then upload the downloaded file through the uploader and analyze it to demonstrate the visitor upload path.
- Analyze the continued invoice and a scanned image. Check page switching, merged results and OCR evidence.
- Prepare Excel, download it and open it in Excel or LibreOffice.
- Click **Clear my documents** in the first window. Verify its history clears while the second window's results remain.
- Check limits using a file exceeding 10 MB or a PDF exceeding five pages. Expect a clear rejection instead of a successful extraction.
- Repeat with your professor's representative, redacted document. Record incorrect fields honestly and demonstrate correction.

## 6. What visitors should know

Session history uses a random capability held in the Streamlit session. It is not an account/login system. A new tab, reload or reconnection may establish a new session; there is no account recovery. Download outputs before leaving. Extracted text and previews remain on server storage until explicitly cleared or that storage is reset, even when the original session is lost. There is no automatic retention timer in this release. Operators should periodically replace/reset the demo instance and monitor disk usage.

The server receives the uploaded bytes for processing and persists extracted results and raster page previews. Public training-approval endpoints are disabled, so public uploads are not added to training data. The internal API enforces session ownership on document reads, edits, previews, exports and deletion. Keep the API private: session capabilities are not a replacement for user authentication or abuse controls.

This release is suitable for a supervised academic demonstration. For broader public traffic, add account authentication, request throttling, a job queue, automatic retention, monitored storage and a reviewed privacy policy. Processing currently permits one extraction at a time; concurrent visitors may see a busy response and need to retry. Arithmetic checks and confidence scores help review; they do not certify a document or guarantee extraction accuracy.

## 7. Troubleshooting

| Symptom | Action |
|---|---|
| Docker named-pipe/daemon error on Windows | Start Docker Desktop, wait until the Linux engine is running, retry `docker info`, then build. |
| Render deploy never becomes healthy | Inspect API startup errors, memory limits, Tesseract installation and `PORT`; use the root Dockerfile and `/_stcore/health`. |
| OCR unavailable | Root image installs Tesseract and English/Hindi language packs. Rebuild that image; check `/health` from inside the container rather than exposing it publicly. |
| File rejected | Use a valid supported file under the configured upload/page limits; remove passwords from PDFs and retry a clear scan. |
| Server busy / 503 | Wait for the other extraction to finish, then click Analyze again. |
| Saved history disappeared | Sessions are temporary and the default filesystem is ephemeral. Reupload the file or use previously downloaded JSON/Excel. |
| Website works but backend unavailable | Keep both processes in the root container; the launcher sets the internal backend URL. Do not deploy only the frontend directory. |
| Container killed during a scan | Inspect host out-of-memory events, increase RAM or reduce page count/image size. |
| Incorrect or missing fields | Inspect the page evidence, correct fields/table rows, save, revalidate and download. Unfamiliar layouts can need manual review. |

## Verification status

Local verification: 42 backend regressions and four rendered Streamlit regressions pass (46 total). A real public-mode API smoke test processed all five included sample types successfully, returned source previews and nine-sheet workbooks, blocked a second visitor from accessing the first visitor's documents, and cleared only the owning session. A rendered AppTest used that live API to analyze the digital sample, prepare Excel and clear the session. These are local checks, not a hosted-browser test. GitHub CI now includes a Docker build and dual-service readiness check; it has not run until the changes are pushed. Docker build and hosted HTTPS acceptance still require a running Docker engine or the selected hosting service; a configuration file alone does not prove a hosted deployment.
