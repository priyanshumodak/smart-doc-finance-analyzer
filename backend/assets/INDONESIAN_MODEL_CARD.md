# Compact Indonesian receipt-line model

Artifact: `indonesian_line_model.json`. Architecture: multinomial Naive Bayes with word and character 3/4-gram counts, row-position features and additive smoothing. It is a field/menu-line classifier, not a translation model and not the neural OCR network.

Trained on 798 unique official CORD-v2 training receipts (10,954 annotated lines); two duplicate training images were excluded. Validation and test records are never fitted. Pixel-level split auditing found no train/evaluation overlap. Classes cover menu, subtotal, tax, total, service, paid amount, change, discount, rounding and other text. See the JSON metadata for class counts, excluded IDs and annotation fingerprint.

The deployment combines this classifier with pretrained RapidOCR/PP-OCRv6 CPU recognition, explicit source labels, locale-aware decimal parsing and arithmetic validation. Low-evidence or learned fallback fields remain reviewable. Probability-like model scores are not calibrated field accuracy; no perfect extraction guarantee is made.

Dataset: CORD-v2 by Park et al., Clova AI/NAVER, https://github.com/clovaai/cord and https://huggingface.co/datasets/naver-clova-ix/cord-v2 . Training data license: CC-BY-4.0. This artifact does not change licenses of upstream data or OCR packages. The original released receipt annotations and original split identities are retained locally. Dataset photos and this model are for Indonesian receipts, not evidence of Indian GST invoice accuracy.

Training: [train_receipt_classifier.py](../../scripts/train_receipt_classifier.py). Full usage and results: [Indonesian extraction guide](../../docs/INDONESIAN_EXTRACTION.md).
