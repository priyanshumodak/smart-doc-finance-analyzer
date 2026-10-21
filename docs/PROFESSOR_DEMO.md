# Professor demonstration and viva

Open `artifacts/PROFESSOR_PRESENTATION.pptx` for the editable slides and speaker notes, or the matching PDF for a viewer-only presentation. The deck reads actual result files when regenerated.

## Before the demonstration

Start the main demonstration in the validation-recommended OCR mode (`scripts/start.ps1 -Mode ocr`). Use token/GPU mode separately to demonstrate trained inference and discuss its review flags.

1. Finish training and check `docs/STATUS.md` or run `scripts/project_status.py`.
2. Confirm `run/upgrade_completion.json` says `complete`. If it is not complete, state which steps are still pending.
3. Open the dashboard and API documentation. Keep `reports/UPGRADE_RESULTS.md` available.
4. Use the supplied synthetic demonstration files first. They are fictional and safe to show. Have an unseen permission-cleared document available for an honest generalization example.
5. Check the selected checkpoint, model execution diagnostics and exported workbook. Do not start a lengthy training job during the presentation.

## Opening explanation: 30 seconds

?Our project turns financial PDFs and scanned images into structured fields and tables. It combines native PDF text or OCR with layout-aware extraction, retains source evidence, checks financial consistency, and lets a person correct and export the result. We trained a token-classification model on fictional Indian GST invoices and report its synthetic performance separately from real-document accuracy.?

## Demonstration: 7-10 minutes

### 1. Digital invoice: two minutes

Upload `sample_docs/demo_digital_invoice.pdf` and click **Analyze documents**.

Expected source values: invoice `DEMO-DIGITAL-2026`, date 01/10/2026, subtotal 100.00, tax 18.00, total 118.00 and one row. Show `pdf_text` as the source. Explain that reliable embedded PDF text avoids unnecessary OCR errors. Choose the total field and point to its highlighted words on the actual page.

Show row multiplication and subtotal/tax/total reconciliation. Explain that the checks compare extracted evidence; an arithmetically consistent but misread invoice still needs review.

### 2. Multipage invoice: two minutes

Upload `sample_docs/demo_continued_invoice.pdf`.

Expected: two pages, one grouped invoice, two rows, subtotal 300.00, tax 54.00 and total 354.00. Expand **Combined results** and show source-page references. Page 1 has no final totals; combined validation uses rows from both pages and totals from page 2.

Explain the conservative grouping rule. This is evidence-based continuation handling, not a promise to group every arbitrary PDF perfectly.

### 3. Review and correction: two minutes

Use a fresh synthetic demo result. For demonstration only, change its total from 118.00 to 120.00 and save. The mismatch should trigger review. Restore 118.00 from the visible source and save again. Show the validation change and `human_review` provenance. Explain that the initial extracted value is retained.

Alternatively correct a real OCR error in an unseen document. Do not present a deliberately altered demo value as a model failure or use the alteration as training truth.

Show the explicit training approval checkbox/button after review. Explain that approval creates eligible aligned training annotations, does not retrain immediately, and excludes reserved evaluation invoices.

### 4. Other financial documents and export: two minutes

Upload `demo_bank_statement.png`, show transaction columns and consecutive balance checks. Upload `demo_financial_report.pdf` if time allows and show its report-specific arithmetic.

Download JSON. Prepare and download Excel. Open **Fields**, **Validation**, **Provenance**, **Document Summary** and **Merged Line Items**. Explain that bank/report extraction is a heuristic extension rather than a separately trained model.

### 5. Results: one minute

Open `reports/UPGRADE_RESULTS.md`. State the exact validation/test size, final selected model, completed updates/epochs and metric scope. Use the matched full-split baseline table when available; older 20-example scores are historical.

Show OCR-only, model-only and combined field scores separately. The combined pipeline can use OCR rules; its score is not standalone LayoutLMv3 accuracy. Mention that table parsing is shared geometry and not a trained table-recognition benchmark.

## Short viva answers

| Question | Answer |
|---|---|
| Why LayoutLMv3? | It combines word content, layout coordinates and visual features for document understanding; our task is BIO token classification over financial fields. |
| Why not OCR alone? | OCR recovers text and positions; structured extraction must identify which value belongs to each field. Rules remain useful and are measured separately. |
| Why native PDF text? | A reliable text layer provides words and coordinates directly. Scans still need OCR. |
| What is BIO? | B marks an entity's first word, I its continuation, O other text. There are 14 entity types and 29 labels including O. |
| What did you actually train? | The full LayoutLMv3 token-classification model in the recorded GPU run; the separate small spatial candidate scorer is an additional baseline. Read metadata for the actual training budget. |
| Are the invoices real? | The 1,000-image training corpus and 500-image external Kirana corpus are synthetic. The local CORD sample contains six real Indonesian receipts, not an Indian invoice benchmark. |
| How is leakage reduced? | Explicit splits and held-out template families, validation-only model selection, preserved publisher test data, and reviewed-data guards for known reserved invoice IDs/hashes. Vendor-independent real evaluation remains future work. |
| Is model confidence a probability of correctness? | It is a model score, not calibrated real-world certainty. OCR and heuristic scores have different meanings. |
| Why can arithmetic pass when extraction is wrong? | Several wrong but mutually consistent values can still reconcile. Source evidence and human review remain necessary. |
| Does a checksum verify GST registration? | No. It validates syntax/checksum consistency locally; no authoritative registration lookup is performed. |
| Can it read handwriting/Hindi? | Tesseract can use installed language packs, but this laptop's verified packs are English/orientation only. No Hindi or handwriting accuracy benchmark is claimed. |
| What happens if the model fails? | Diagnostics show the failure, and available OCR rules can supply fields. The app flags uncertainty rather than claiming the model succeeded. |
| Why are old and new F1 values different? | Training budget, model weights and sometimes evaluation sample sizes differ. Compare models on the same full split for a fair claim. |
| What remains? | Permission-cleared varied real invoice annotation, independent vendor/layout evaluation, trained table structure, broader language/handwriting tests and multi-user deployment work. |

## Suggested presentation sequence

1. Problem: manual financial-document entry and verification.
2. Objectives: structured fields/rows, inspectable evidence, reconciliation and review.
3. Architecture: PDF/OCR -> model/rules -> tables -> validation -> review/export.
4. Dataset: provenance, labels, split policy, synthetic limitations.
5. Training: recorded settings, validation selection, final held-out evaluation.
6. Demonstration: use the sequence above.
7. Results: exact metrics, test counts and latency scope.
8. Limitations and next work: explain honestly.

## Claims to avoid

Do not say 100% accurate, production-ready, trained on 1,500 real invoices, trained table detection, verified Hindi recognition, or full CORD/FUNSD benchmark. Do not describe model execution as model contribution: show accepted final field sources. A review-needed unseen invoice is useful evidence of the system's limits, not something to hide.
