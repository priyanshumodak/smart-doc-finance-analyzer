ÃƒÂ¯Ã‚Â»Ã‚Â¿# Extraction and training upgrades

This document describes the second implementation round. Original baseline measurements remain in `reports/PROJECT_RESULTS.md`; new results are recorded separately so old scores are not silently relabelled.

## Use the new features

Open http://127.0.0.1:8501 and refresh. Reprocess an old result if it has no preview; older history records did not store processed page images.

- Upload `sample_docs/demo_digital_invoice.pdf`. It contains embedded text and should display **Text source: embedded PDF text**.
- Under **Highlight a field**, select an invoice number, amount or vendor. Orange boxes mark the selected source words on the real processed page. Missing alignment is shown explicitly instead of highlighting unrelated text.
- Upload `sample_docs/demo_continued_invoice.pdf`. Expand **Combined results**: two pages belong to one invoice, and their line items reconcile together. Different invoice numbers remain separate documents.
- Expand field provenance to inspect independent model/rule candidates, confidence rejection reasons, format checks and selection rationale. Conflicting credible values require review even when one passes arithmetic.
- Upload `demo_bank_statement.png`. Edit dated debit/credit/balance rows under **Review transactions**, save and inspect refreshed balance checks.
- After checking an invoice page and saving corrections, expand **Save a reviewed training example**. Explicitly confirm the source check before approving. Corrected values absent from source tokens remain pending annotation; reserved validation/test invoices are blocked.

## Reviewed-data training loop

```powershell
.\backend\venv\Scripts\python.exe scripts/export_reviewed_dataset.py --out data/reviewed_training_v1
```

Only approved, aligned rows enter `annotations.jsonl`. Pending text alignment is saved separately. Editing an approved page invalidates its previous approval. Processed images and review records are stored locally with the document history; raw uploaded files are not retained.

Use the approved train-only supplement alongside the original independent splits:

```powershell
.\.gpu-venv\Scripts\python.exe notebooks/finetune_layoutlmv3.py --data_dir data/training_indian_invoices --reviewed_data data/reviewed_training_v1 --output_dir models/reviewed-v1 --epochs 3 --batch_size 1 --max_length 256 --gradient_checkpointing
```

Real-world improvement still requires varied, permission-cleared Indian invoices and manually checked labels. The existing CORD sample contains Indonesian receipts and is not a substitute for that corpus. No private or unclear-license invoice collection was silently imported.

## GPU setup and training

The CUDA environment is separate from `backend/venv`:

```powershell
.\scripts\setup_gpu.ps1
.\scripts\train_gpu.ps1 -Output models/layoutlmv3-gpu-v2 -Epochs 3
```

The setup uses the official PyTorch 2.3.1 CUDA 12.1 wheel. The 4 GB GPU configuration uses batch size one, mixed precision, 256-token word-aligned windows and encoder checkpointing. Transformers 4.42 implements LayoutLMv3 encoder checkpointing but does not advertise top-level support; the training script includes a compatibility adapter rather than patching the installed package. Input windows preserve all source words and avoid cutting BIO entities when possible.

Training uses all 700 training examples, validation for checkpoint selection and the 150-example test split after training. Metadata records actual completed steps/epochs. A run is not considered complete merely because it has a metadata file.

After a finished run:

```powershell
.\backend\venv\Scripts\python.exe scripts/select_model.py --candidate models/layoutlmv3-gpu-v2
.\scripts\stop.ps1
.\scripts\start.ps1 -Mode token -UseGpu
```

`select_model.py` compares validation F1 with the original baseline and records the preferred checkpoint. It never selects using test scores. Without `-UseGpu`, the app uses its CPU environment.

## Measure output quality

```powershell
.\.gpu-venv\Scripts\python.exe scripts/compare_modes.py --model models/layoutlmv3-gpu-v2 --offset 20 --limit 10 --out reports/v2_comparison
.\backend\venv\Scripts\python.exe scripts/benchmark_pdf_paths.py
```

The mode comparison reports field-value precision/recall/F1, exact full line-item row F1, source counts and latency for OCR rules, model-only fields, and combined extraction on identical documents. Table parsing is shared geometry; row scores are not neural table-recognition or GriTS scores. Do not tune against the reserved slice after viewing its scores.

The native PDF timing comparison is on two generated demonstration files. It is a functional timing check, not a performance guarantee or real-world accuracy benchmark.

## Research sources and implementation choices

- [pdfplumber official documentation](https://github.com/jsvine/pdfplumber): embedded word boxes, PDF rasterisation and table APIs. Used for the new digital-PDF path; sparse/junk text layers fall back to OCR per page.
- [Hugging Face LayoutLMv3 documentation](https://huggingface.co/docs/transformers/model_doc/layoutlmv3): token classification using supplied words/boxes with `apply_ocr=False`.
- [Official PyTorch version instructions](https://pytorch.org/get-started/previous-versions/): matching CUDA 12.1 packages for the installed Torch version.
- [Microsoft Table Transformer](https://github.com/microsoft/table-transformer): a relevant trained table-structure approach. This project currently improves header/column geometry, wrapped descriptions, HSN/discount/tax columns and continuation handling; it does not claim to have trained or integrated TATR.
- [Official CORD release](https://github.com/clovaai/cord): real receipt data and semantic annotations, with the original split and attribution retained by the importer.

## Scope and remaining work

The implementation improves document handling, evidence, review and reproducible training. Synthetic model scores do not establish performance on real vendors, handwriting or Hindi documents. Large-scale real-document evaluation and trained table-structure recognition remain separate work. A real invoice corpus requires documents you are allowed to use; the reviewed-data workflow is ready for them.

Training policy: three epochs is the maximum. A validation entity F1 target of 0.99 is declared before the first validation pass; a complete saved checkpoint may be finalized early when that target is reached. Actual selected steps/epochs and the stopping reason are recorded. This is a synthetic target and does not establish real-world accuracy.


## Additional external invoice corpus

The [publisher's Kirana dataset](https://huggingface.co/datasets/build-small-hackathon/kirana-invoice-train-data) provides 500 CC0 synthetic Indian FMCG invoice images across printed GST, Tally-style, simulated handwriting and WhatsApp-style layouts. It is downloaded to `data/kirana_external`, with 405 train, 45 validation and the publisher's 50 test examples preserved. It is not mixed into the current LayoutLMv3 run: publisher JSON does not provide the word boxes/BIO labels required by that trainer.

The importer retains original publisher annotations, hashes images and maps partial schemas. A visual spot-check of training example `kirana_train_00000` found rounded displayed row rates/amounts while JSON retained decimals. Audit and align annotations to visible text before exact row scoring or token training. This is external synthetic data, not real customer invoices.

To import into a new folder: `backend/venv/Scripts/python.exe scripts/download_kirana.py --out data/kirana_new`. To repair an earlier import's schema without downloading images again: `backend/venv/Scripts/python.exe scripts/refresh_kirana_annotations.py`.

## Five-minute professor demonstration

1. Open http://127.0.0.1:8501 and upload `sample_docs/demo_digital_invoice.pdf`. Show the native PDF text source, extracted fields, items and arithmetic checks.
2. Select an extracted field in the source preview and show its highlighted evidence. Explain that confidence and arithmetic checks support review; neither guarantees correctness.
3. Upload `sample_docs/demo_continued_invoice.pdf`. Expand combined results: two pages form one invoice with two merged rows. Show per-page evidence and the combined Excel sheets.
4. Upload a bank-statement demo. Edit a transaction, save the correction and show balance reconciliation. For an invoice, save corrections and explicitly approve eligible aligned pages for future training; evaluation examples remain blocked.
5. Download JSON and Excel. Open `reports/UPGRADE_RESULTS.md` to discuss measured tests, synthetic model scores and the same-document OCR/model/combined comparison. Explain that real-document accuracy still requires independently annotated real invoices.

Old history records should be re-uploaded to obtain newly generated source previews and summaries. For a reliable presentation, use the supplied demo files first, then try an unseen document and openly show any review flags.

## Current long-running job

The completion worker `scripts/finish_upgrade.ps1` waits for training, selects using validation only, measures the same reserved test slice in all modes, restarts the app with GPU inference, verifies live uploads, updates the report and rebuilds the archive. Status is in `run/upgrade_completion.json`; output is in `run/upgrade-finish.log` and errors in `run/upgrade-finish-error.log`. Keep the computer awake until it finishes. If Windows restarts, resume the saved checkpoint with the trainer's `--resume_from_checkpoint` option, then run the completion worker again. Do not start duplicate workers.


Recovery note: the first unattended completion attempt stopped after successful training/baseline evaluation because its Windows-written policy JSON had an encoding marker. The reader now accepts UTF-8 with or without that marker. The resumed job reuses completed evaluation, and its log/error files are `run/upgrade-finish-resume.log` and `run/upgrade-finish-resume-error.log`. `run/upgrade_completion.json` is the current workflow state; older log files are retained as history.


## Final operating recommendation

The completed run trained for three epochs/2,100 updates and validation retained the step-700 checkpoint. Full-split entity F1 is 0.842 validation and 0.875 test. For actual field extraction, validation favored OCR rules (0.923 field F1 versus combined mode 0.732), so the main app/demo uses `scripts/start.ps1 -Mode ocr`. On a separate reserved 20-document synthetic test slice, this selected mode reached 0.953 field F1 and 0.932 field accuracy. Trained CUDA inference is separately verified and remains available with `-Mode token -UseGpu`. Read `docs/RETURN_FROM_AFK.md` for the final handover and avoid equating entity F1 with pipeline accuracy.
