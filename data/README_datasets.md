# Dataset sources and the generated training set

## Available locally

`training_indian_invoices/`: 1,000 fictional Indian GST invoice images, exact renderer word boxes and 29 BIO/O labels covering 14 financial fields, key/value relations, financial ground truth and deterministic splits (700 train / 150 validation / 150 test). Do not treat this as a real-world benchmark or Hindi dataset. See `manifest.json` and `reports/dataset_validation.json`.

Generate another dataset:

```powershell
.\backend\venv\Scripts\python.exe data/build_training_dataset.py --n 1000 --out data/new_dataset --seed 99
```

## Verified public sources

- **CORD-v2:** [official repository](https://github.com/clovaai/cord), [official Hugging Face release](https://huggingface.co/datasets/naver-clova-ix/cord-v2). The released dataset has 1,000 Indonesian receipts (800/100/100), OCR word boxes and fine-grained receipt annotations. CC-BY-4.0. This is receipt data, not an Indian GST invoice corpus.
- **FUNSD:** [author's dataset page](https://guillaumejaume.github.io/FUNSD/). 199 annotated noisy forms with semantic entities and relations. Use the original form schema for FUNSD benchmark comparisons; invoice field F1 is a different task.
- **SROIE:** [official ICDAR challenge](https://rrc.cvc.uab.es/?ch=13). Scanned-receipt OCR and key-information extraction. Follow the challenge's dataset access and usage terms.
- **AjitRawat/invoice:** [dataset page](https://huggingface.co/datasets/AjitRawat/invoice), 22 image/JSON rows. Small, inconsistently annotated; no clear license displayed on the page checked. Obtain permission/clarification before training or redistribution. It was not downloaded into this project.

The earlier placeholder “Indian Financial Documents Dataset” was not verified and has been removed.

## Import CORD

```powershell
.\backend\venv\Scripts\python.exe scripts/download_cord.py --limit 2 --out data/cord_v2_sample
.\backend\venv\Scripts\python.exe scripts/download_cord.py --transport streaming --limit 0 --out data/cord_v2
```

`--limit` is per original split; zero with `--transport streaming` imports the full released dataset. The default viewer transport is for small cached subsets. The full download can be several GB. The adapter retains the source, original splits, image/annotation hashes and CC-BY-4.0 notice. Only total, subtotal and tax categories are mapped to the finance schema; all other tokens are labelled O. It preserves IDR currency and never invents GSTIN/PAN labels. Long receipts can exceed the training context and require chunking before training.

## Real Indian invoices

For a stronger project report, obtain permission to use varied, redacted invoices from several vendors, manually annotate the required fields/boxes and keep an independent vendor/layout test set. Preserve source provenance, annotation conventions and separate validation/test records. Do not mix synthetic validation results with real-document results.

## Metrics

- Training script: BIO entity precision/recall/F1 using supplied tokens/boxes.
- `benchmark_pipeline.py`: final field precision/recall/F1/accuracy after actual OCR and fallback rules, on first-page fields.
- `train_relations.py`: candidate-pair relation precision/recall/F1 using supplied spans.

Keep these scopes separate in the report and cite source datasets/models.

## Additional verified external Indian corpus

[build-small-hackathon/kirana-invoice-train-data](https://huggingface.co/datasets/build-small-hackathon/kirana-invoice-train-data) is marked CC0-1.0 by its publisher and contains 500 **fully synthetic** Indian FMCG invoices. Its four formats include printed GST, Tally-style, simulated handwriting and WhatsApp-style images. It is useful for layout/domain-shift evaluation but is not a real customer-invoice dataset.

```powershell
.\backend\venv\Scripts\python.exe scripts/download_kirana.py
```

The importer retains the publisher's 50-example test split and creates a seeded 45-example validation subset from the 450 publisher training examples (405/45/50). It preserves financial JSON and partial annotation masks; it does not invent token labels or silently repair publisher annotations. The current GPU model is trained on this project's original 700 images, not this external corpus, so its test examples can provide a separate cross-layout check.

Another checked source, `processvenue/INVOICE_ANNOTATION_V2`, supplies a licensed CSV of field annotations but no corresponding images in the checked repository. It is not treated as a ready image-training corpus. FATURA2 provides generated templates rather than real invoices. Permission-cleared real invoice images still need to be collected and checked separately.

## Implemented real-image workflow

See [real receipt data, evaluation and training](../docs/REAL_DATA.md). The new `data/cord_real_v2` subset has 60 real receipts with corrected value-only labels and three-field evaluation masks. The earlier six-image importer output is retained as legacy data; use the new import for metrics and training.
