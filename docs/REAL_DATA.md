# Real receipt images: data, evaluation and training

## What is implemented

The project now includes a reproducible importer for **real CORD-v2 receipt photographs**, a 60-image local subset, checked official train/validation/test separation, original annotations, image and annotation hashes, a small separately trained GPU pilot, and a real-image section in the website.

CORD-v2 is released by Clova AI/NAVER under **CC-BY-4.0**. The public release contains 1,000 Indonesian receipts (800 train / 100 validation / 100 test). These are real receipts with IDR currency, not Indian GST invoice images. Sources: [official repository](https://github.com/clovaai/cord), [publisher dataset](https://huggingface.co/datasets/naver-clova-ix/cord-v2), [license](https://creativecommons.org/licenses/by/4.0/).

Our subset is the first 20 examples of each original split: **20 train, 20 validation, 20 test**. This convenient subset is not a representative large-scale benchmark. No split was shuffled into another split.

## Try real images on the website

1. Open **Try real receipt images (CORD)**.
2. Choose one of three real receipts, optionally enable **Preview the real receipt**, then click **Analyze real receipt**.
3. OCR runs on the actual JPEG. The published values appear separately under **Published dataset values for comparison**. They are never passed into extraction.
4. Compare the source, extracted fields and the three published reference amounts. References are in IDR; separators can differ from Indian amounts.
5. Use **Review and correct**, save corrections, and download JSON/Excel as before. A review-required status on these unfamiliar receipts is expected and should be explained honestly.
6. You can download a real image and upload it through the normal uploader to demonstrate that it is a real file, not a stored answer.

Only three **training-split** examples are shipped publicly, with license, attribution and source hashes in `sample_docs/real_receipts`. Validation and test images remain local and ignored by Git. The dataset publisher already obscures some information in released photos; do not infer missing store or payment labels.

## Download and verify data

From the repository root, using the existing CPU environment:

```powershell
.\backend\venv\Scripts\python.exe scripts/download_cord.py --limit 20 --out data/cord_real_v2
.\backend\venv\Scripts\python.exe scripts/validate_real_dataset.py --data data/cord_real_v2
```

The 60-image download is already present in this workspace. The importer refuses to overwrite an existing directory. Choose a new output directory for another download.

The default viewer transport downloads cached official preview rows and their publisher JPEG assets, checking image dimensions against annotations. Available cached row counts vary; it refuses truncated annotations and refuses silently shortening a requested split. This avoids downloading large parquet shards for a small experiment. Signed asset URLs are not retained as durable identifiers; source indices, the dataset revision observed at download, actual bytes and hashes are retained. Viewer cache responses are not guaranteed to be an immutable historical snapshot; raw annotations are saved for reproducibility.

For the complete public release, use the streaming transport (several GB of network/cache storage can be required):

```powershell
.\backend\venv\Scripts\python.exe scripts/download_cord.py --transport streaming --limit 0 --out data/cord_full_v2
.\backend\venv\Scripts\python.exe scripts/validate_real_dataset.py --data data/cord_full_v2 --out reports/cord_full_validation.json
```

Streaming uses the resolved dataset revision and requires the optional `datasets` dependency in `notebooks/requirements.txt`. The viewer path needs only Requests and Pillow. Images, annotations and trained weights stay out of GitHub; the small licensed demo subset is explicitly allowlisted.

## What is annotated and scored

The adapter maps only:

| CORD category | Project field |
|---|---|
| `total.total_price` | `total_amount` |
| `sub_total.subtotal_price` | `subtotal` |
| `sub_total.tax_price` | `tax_amount` |

Canonical target amounts come from official `gt_parse`, not strings combining `TOTAL` with an amount. BIO training labels mark value words where official `is_key=0`; printed key words remain O. All other categories remain O. GSTIN, PAN, seller identity, invoice IDs and line-item relations are not invented or scored as annotated fields.

Field evaluation respects the three-field annotation mask and IDR thousands separators, without changing Indian decimal normalization. Original words/boxes are used only for the token-training experiment, not substituted for OCR when evaluating extraction.

## Evaluate actual OCR and extraction

```powershell
.\backend\venv\Scripts\python.exe scripts/benchmark_pipeline.py --data data/cord_real_v2 --split test --limit 20 --mode ocr --out reports/real_receipts/ocr_test
```

Completed baseline on the 20 official test-subset receipts:

- 40 supported field values; 7 correct matches, 3 false positives, 33 false negatives.
- Precision **70.0%**, recall **17.5%**, field F1 **28.0%**, field accuracy **17.5%**.
- All 20 documents required review under the existing document validation rules.

This is a real domain-shift result, separate from the much stronger synthetic Indian invoice results. It establishes neither general real-invoice accuracy nor readiness to automate these receipts.

## Separate real-data GPU training pilot

A one-epoch classifier-head-only pilot has completed in `models/layoutlmv3-cord-real-pilot`, initialized from `models/layoutlmv3-gpu-v2`. It used the 20 real training examples, the 20 validation examples for checkpoint selection, seed 42, batch size one and 256-token windows. The encoder was frozen. The original model and Cloud OCR configuration were preserved.

Reproduce into a new model output directory:

```powershell
.\.gpu-venv\Scripts\python.exe notebooks/finetune_layoutlmv3.py --data_dir data/cord_real_v2 --model_name models/layoutlmv3-gpu-v2 --output_dir models/layoutlmv3-cord-real-pilot-v2 --epochs 1 --freeze_backbone --max_length 256 --batch_size 1
```

Pilot results using supplied words/boxes: validation entity F1 **21.05%**, test entity F1 **33.71%**. These token/entity metrics are not comparable with end-to-end field F1. They do not prove that deploying the pilot would improve uploaded-photo extraction. The small head-only experiment is a working real-data training demonstration, not a production model upgrade.

Actual OCR-plus-pilot evaluation uses the same held-out receipts:

```powershell
.\.gpu-venv\Scripts\python.exe scripts/benchmark_pipeline.py --data data/cord_real_v2 --split test --limit 20 --mode token --model models/layoutlmv3-cord-real-pilot --out reports/real_receipts/token_test
```

Generated reports remain in `reports/real_receipts`. A concise checked-in result summary is linked from the repository results page. Do not tune on the reported test examples. Further experiments should declare settings in advance and use validation for model selection; retain an additional unseen test set if the current test examples influence development.

## Improve beyond this pilot

Import the full release, inspect label coverage, train on the full official training split and select configurations on validation. Add language/locale-aware extraction and evaluate OCR errors separately from token labeling. For Indian GST invoices specifically, collect permission-cleared real Indian invoices with accurate annotation and vendor/layout-separated splits: CORD does not supply that domain.

## Completed pilot end-to-end comparison

On the same 20 held-out receipts and 40 annotated values, OCR/rules field F1 was **28.00%** (7 TP, 3 FP, 33 FN). OCR plus the pilot model scored **23.73%** (7 TP, 12 FP, 33 FN). Both had **17.5% field accuracy**. Every document required review. The small pilot added false positives and is **not promoted** to the website. The website continues to use OCR/rules. Further model selection must use validation, not optimize these published test results.

Historical pilot verification: **54 regressions passed**: 47 backend/data tests, four original dashboard tests and three Cloud entrypoint tests, including actual real-receipt OCR and a check that published reference answers are not passed to extraction.

## Updated Indonesian extraction

The small pilot above is historical. The latest pipeline uses the full real release, duplicate-protected training, stronger OCR and original-language extraction. See [the Indonesian extraction guide](INDONESIAN_EXTRACTION.md) for the deployed configuration and its separate test results.
