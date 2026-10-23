# Recorded local results

This is a curated public snapshot of the completed local run. Generated reports, inference outputs, document previews and personal runtime state are excluded from Git.

## Model training

- Dataset: 1,000 fictional Indian GST invoices; 700/150/150 train/validation/test.
- Run: full fine-tuning, three epochs, 2,100 optimizer updates, batch size one, 256-token word-aligned windows.
- Validation selected the step-700 (epoch-one) checkpoint; later weights were not automatically preferred.
- Both models below were evaluated on the same 150-example validation and 150-example test splits.

| Model | Validation BIO entity F1 | Test BIO entity F1 |
|---|---:|---:|
| Initial bounded baseline | 0.4253 | 0.4385 |
| Selected GPU-trained model | 0.8419 | 0.8748 |

BIO metrics use supplied words/boxes and are not OCR or final-invoice accuracy.

## Recommended operating mode

On the same 20 synthetic validation documents, OCR-rule final-field F1 was 0.923 versus 0.732 for combined token mode. OCR was selected as the default without changing weights or extraction rules.

A separate reserved 20-document synthetic test slice, measured after mode selection, gave OCR field F1 **0.953** and field-value accuracy **0.932** (205 correct annotated values out of 220). The earlier diagnostic test comparison motivated checking operating modes; it is not claimed as an untouched mode-selection test.

The trained model was separately exercised through the HTTP API on CUDA with 14 accepted field predictions. A Windows first-upload CUDA crash was resolved by initializing model libraries during server startup.

## Functional checks and limitations

- 43 local regression tests passed: 39 backend and four rendered-dashboard checks. GitHub preparation also verified all 43 from an isolated source-only checkout without model weights, generated/downloaded datasets or installed environments inside that checkout.
- Real HTTP uploads verified OCR extraction, native multipage grouping, source previews and Excel downloads.
- Dataset integrity checked image hashes, labels, split membership and financial consistency.
- An external five-image synthetic Kirana validation check was weak: OCR recovered 3/20 annotated fields; combined mode recovered 4/20. This is a domain-shift limitation, not a real-document benchmark.
- No real Indian-invoice, Hindi, handwriting, full CORD/FUNSD or trained table-structure benchmark is claimed.

The repository ships generator code rather than the local corpus/weights. Fonts, platform and dependency differences can change regenerated images and scores. Detailed local artifacts can be recreated using the training/evaluation scripts; original local history and reviewed financial records are not included.

Real-document results are reported separately in [the CORD receipt experiment](REAL_RECEIPTS.md).

Latest real-image improvement: [Indonesian extraction comparison](INDONESIAN_EXTRACTION.md), evaluated on 80 reserved test receipts.
