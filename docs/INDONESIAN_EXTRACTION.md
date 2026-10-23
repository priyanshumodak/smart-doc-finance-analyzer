# Indonesian receipt extraction

The application preserves original Indonesian OCR text and item descriptions. Choose **Bahasa Indonesia receipt (IDR)** under **Document language / receipt format**, upload a photo and analyze it. The three CORD demo buttons select this profile automatically. **Field labels** can be displayed in English or Bahasa Indonesia. This changes field headings, not product names, amounts or the entire receipt text.

## What changed

- Compact PP-OCRv6 neural OCR via RapidOCR 3.10.0 and ONNX Runtime 1.20.1 on CPU. Model files are bundled with the installed wheel; no paid API or separate model server is required.
- Tesseract remains available, now with Indonesian language data and source-quality fallback. Low-resolution images can be upscaled; segmentation variants are compared using recognized text and visible financial-label coverage, never reference answers.
- Perspective-aware row association uses detected quadrilaterals to prevent a tax label being paired with a service amount from the next row. Displayed evidence boxes remain in the selected source image's coordinates.
- Long receipts are read in overlapping strips, retaining small text and deduplicating overlap in original coordinates.
- IDR `60.000`, `60,000` and `Rp 60.000` are normalized to the numeric string `60000`, with currency IDR. Original labels and amount text remain in provenance alongside the source OCR.
- A separately trained compact receipt-line classifier supports field and menu recognition. It runs without PyTorch in the hosted application.
- Subtotal, tax, service charge, total, amount paid, change, discount and rounding have receipt-specific label handling. Item names stay in their source language. Missing quantities and unit prices remain empty unless observed; unit rates are accepted only when printed values and row arithmetic support them.
- Receipt reconciliation includes observed service charges and change. Indian GSTIN/PAN and mandatory invoice-number rules are not imposed on Indonesian receipts. Unsupported or redacted metadata is not invented.

## Using it

1. Open the app and select **Bahasa Indonesia receipt (IDR)** for Indonesian receipt uploads. Auto-detection is available, but explicit selection avoids ambiguity with other countries' numeric formats.
2. Analyze the image or use **Try real receipt images (CORD)**.
3. Select **Bahasa Indonesia** or **English** under **Field labels**.
4. Expand **Original Indonesian evidence and English labels** to compare printed labels/amounts with normalized IDR values. The original OCR text and source preview are retained.
5. Review amounts and item rows. Blank fields were not reliably read; published CORD images obscure some store/payment details, which cannot be recovered from the image.
6. When you have checked every displayed value, select **I checked every displayed value against the source**, then save corrections and revalidate. This explicitly confirms unchanged fields too; unresolved arithmetic/missing-data issues still remain. Download JSON or Excel afterward. Field exports include locale and currency; provenance includes source labels, amounts, engine selection and evidence.

Examples: `PB1` / `Pajak` maps to Tax; `SVC CHRG` / service maps to Service charge; `Tunai` maps to Amount paid; `Kembalian` maps to Change. These are financial-label mappings, not a general document translation model.

## Real-data training and leakage protection

The complete official CORD-v2 release is downloaded locally: **800 train, 100 validation, 100 test**. Its two byte- and pixel-identical training duplicates are excluded, leaving **798 unique training receipts** and **10,954 labeled lines** for the compact classifier. No validation/test pixels overlap the retained training set. Original public split membership is retained in the dataset; deduplication affects fitting, not publisher records.

The classifier uses word features, character 3/4-grams and coarse row position in a multinomial Naive Bayes model with additive smoothing. Learned fallback predictions require visible amounts, a high model score and human-review marking. Scores are not calibrated probabilities of financial correctness. Explicit source labels and arithmetic checks remain independent evidence. This model is not the earlier one-epoch LayoutLMv3 pilot, which was not promoted.

Weights: `backend/assets/indonesian_line_model.json`. Training code: `scripts/train_receipt_classifier.py`. Dataset and split audit: `scripts/audit_receipt_splits.py`. Large datasets, detailed reports, neural packages and the old GPU checkpoint remain outside Git; the compact deployed classifier is intentionally included.

## Reproduce

Using Python 3.11 from the repository root:

```powershell
python -m pip install -r requirements.txt -r notebooks/requirements.txt
python scripts/download_cord.py --transport streaming --limit 0 --out data/cord_real_full --resume
python scripts/validate_real_dataset.py --data data/cord_real_full
python scripts/audit_receipt_splits.py --data data/cord_real_full --out reports/indonesian/split_audit.json
python scripts/train_receipt_classifier.py --data data/cord_real_full --split_audit reports/indonesian/split_audit.json
python -m streamlit run streamlit_app.py
```

Full download is several GB. The importer preserves completed image/annotation pairs, checks source dimensions, retains original annotations and hashes, handles repeated reference totals without silently choosing one, and enforces official full split counts. Resuming complete splits avoids another remote image scan. For a small experiment, use a new folder with `--limit 20` and the default viewer transport.

On Windows, install Tesseract and Poppler using the existing installation guide. Optional local Indonesian Tesseract language cache:

```powershell
python scripts/setup_indonesian_ocr.py
```

Cloud installs `tesseract-ocr-ind` from `packages.txt`. Neural OCR requires the pinned `rapidocr` and `onnxruntime` packages. ONNX Runtime 1.31.0 caused a native access violation during local integration; 1.20.1 was tested successfully and is pinned. OCR and OpenCV thread counts are bounded.

## Evaluation scope

Development used official validation receipts. The final test comparison uses official test indices **20 through 99**: 80 receipts excluded from development. Earlier test indices 0 through 19 were already used in prior experiments and are excluded from this final comparison. Both the archived old pipeline and the new pipeline read the exact same original image files. Only subtotal, tax and total have mapped reference fields for this comparison; other extracted fields and full item text are not established by that score.

The result table and supported claims are in [the Indonesian extraction results](results/INDONESIAN_EXTRACTION.md). Do not treat passed arithmetic checks or successful demos as proof of perfect transcription. Faint, blurred, redacted or unseen layouts can still need review.

Sources: [CORD](https://github.com/clovaai/cord), [RapidOCR](https://github.com/RapidAI/RapidOCR), [RapidOCR installation/model documentation](https://rapidai.github.io/RapidOCRDocs/main/en/model_list/), [Tesseract quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html).

Final reserved-test result: **17.30% to 86.00% amount-field F1**, **92.81% precision**, and **80.12% annotated-value accuracy**, on 80 receipts and 161 supported values. These scores cover subtotal/tax/total, not every word or every possible field.
