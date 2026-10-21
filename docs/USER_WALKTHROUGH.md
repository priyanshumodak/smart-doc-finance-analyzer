# User walkthrough

## Upload and inspect

1. Open the dashboard. The sidebar reports OCR availability and the extraction mode.
2. Select one or several PDF, PNG, JPG/JPEG or TIFF files. The default backend limit is 20 MB and 20 pages per document.
3. Click **Analyze documents**. Several uploads are processed sequentially. Use **Batch document** and **Review selected document** to switch results.
4. Choose the page. Each page records its text source, tokens, fields, tables and validation results.
5. Select **Highlight a field**. Orange rectangles identify the selected source words on the processed page. A manually entered value absent from source tokens may have no evidence rectangle; a highlight is not fabricated.
6. Toggle **Show all word boxes** for a layout check. The boxes correspond to the displayed processed page, including scan preprocessing.
7. Inspect OCR text and source information. Native PDF words have no OCR confidence; a missing confidence is not a zero score.

For digital PDFs, reliable embedded text bypasses OCR. Scans and sparse/junk text layers fall back to OCR independently on each page. Native pages are not deskewed because that would invalidate their PDF coordinates.

## Interpret the result

- `ok`: available validation checks passed without current blocking review reasons; it is not a guarantee that every extracted field is correct.
- `review_needed`: conflicting/invalid values, weak or unreadable source evidence, or failed arithmetic need attention.
- `insufficient_data`: required evidence for reconciliation is absent.

Model confidence, OCR confidence and heuristic ranking are different quantities. Model confidence is not calibrated certainty. Candidate lists retain alternatives; arithmetic can help rank observed valid candidates but cannot invent a value absent from the page.

## Multipage documents

Upload `sample_docs/demo_continued_invoice.pdf`. Expand **Combined results** to see two pages grouped into one invoice with page provenance and merged rows. Consecutive matching invoice numbers or explicit continuation markers permit grouping. Distinct invoices remain separate. Unclear continuation without identifying evidence may remain separate for review.

Combined validation can reconcile rows from earlier pages with totals printed on the last page. Per-page checks may be incomplete even when the combined invoice reconciles.

## Correct invoice fields and rows

1. Compare every important value with the source.
2. Edit the value column. Field names, recorded source and confidence are read-only.
3. Add, remove or correct line-item rows as required; retained HSN/discount/tax columns remain available when extracted.
4. Click **Save corrections and revalidate**.
5. Confirm the updated checks and document summary. Human corrections have `human_review` provenance; the initial extracted values remain in the saved result.

Explicit row tax percentages and discounts can support inclusive/exclusive arithmetic. Hidden precision, ambiguous columns and unprinted tax bases require review rather than guessed numbers.

## Bank statements and reports

Upload `demo_bank_statement.png` for transactions. Edit debit, credit and balance values in the transaction grid, save and inspect `previous balance - debit + credit == balance`. Without an opening balance, the first transaction cannot be fully checked. Transaction/report extraction uses inspectable rules and is not a separately trained bank model.

Upload `demo_financial_report.pdf` for revenue, expenses and profit checks. The app checks their relationship when those values exist. It does not impose invoice-only fields on statement/report pages.

## Approve an invoice page for future training

1. Save reviewed corrections first.
2. Check **I checked this page against its source**.
3. Click **Approve page for training**.
4. Read the returned eligibility/alignment status.

Approval is explicit and separate from saving. Only invoice/receipt pages with acceptable validation and a stored preview can be approved. Reserved validation/test invoices are blocked. Corrected values that do not align with source words remain pending instead of becoming invented BIO labels. A later correction invalidates the previous approval and requires a fresh check. Approval does not trigger immediate retraining.

Export approved aligned examples with the command in [training instructions](TRAINING_AND_DATA.md). Manually verify any OCR token errors before using real documents for training.

## Export and reopen

Click **Download JSON** for structured results, provenance and diagnostics. For Excel click **Prepare Excel download**, then **Download Excel**.

| Excel sheet | Contents |
|---|---|
| Fields | Per-page field values and validation status |
| Line Items | Per-page rows including retained extra columns |
| Validation | Financial checks, balance checks and validation issues |
| Provenance | Source/confidence/candidate/evidence records |
| Transactions | Bank rows |
| Financial Metrics | Report figures |
| Spatial Relations | Inspectable key/value candidate links |
| Document Summary | Combined document values and contributing pages |
| Merged Line Items | Combined invoice rows with page provenance |

Use sidebar filename search and **Open saved document** to reopen a result. The app retains local history and processed images. A fresh upload creates a new result; it does not overwrite the old document.


## Which mode should I demonstrate?

Use OCR mode for the main working demonstration: validation selected it for higher final-field quality. To demonstrate the trained component, stop the app and start `scripts/start.ps1 -Mode token -UseGpu`, upload a demo, and expand **Full validation and extraction provenance**. The token-model diagnostics show checkpoint, device, executed status and accepted fields. Model mode can produce more review flags; do not present its BIO entity score as final-field accuracy. Stop/restart in OCR mode afterward for the recommended workflow.
