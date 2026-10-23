# Indonesian receipt extraction: final comparison

23 October 2026. Evaluation uses the same 80 original CORD-v2 test images, indices 20-99, held out from this project's fitting and development. Earlier test indices 0-19 were used in historical experiments and are excluded. Source files and reference masks are identical for both methods. Upstream pretrained OCR data have not been independently audited.

Only subtotal, tax and total are mapped for this benchmark: **161 annotated values**. Unknown invoice fields are excluded; IDR formatting is normalized. This is not an all-fields, item-text, translation or general real-world accuracy result.

| Method | TP | FP | FN | Precision | Recall | Field F1 | Annotated-value accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Previous pipeline | 16 | 8 | 145 | 66.67% | 9.94% | 17.30% | 9.94% |
| Upgraded Indonesian profile | 129 | 10 | 32 | 92.81% | 80.12% | 86.00% | 80.12% |

The old pipeline is preserved from commit `9059b8c` in an isolated source checkout and runs its original general OCR settings. The upgraded pipeline uses the explicit `id-ID` receipt profile, bundled PP-OCRv6 CPU recognition, source-based OCR selection, perspective-aware rows, IDR parsing, receipt-specific rules and a trained line classifier. Both read the exact same original images. The model and settings were fixed before examining this final test result.

The classifier was trained on **798 unique images / 10,954 labeled lines** from the official 800-image training split. Two pixel-identical training duplicates were excluded: `cord_train_00109` and `cord_train_00285`. Pixel auditing found 998 unique images in the 1,000-image release and no train/evaluation overlap. No validation or test records are fitted.

The final configuration scores **92.11% field F1** on the first 20 official validation receipts (35 TP, 2 FP, 4 FN, 39 supported values). Earlier development runs used validation receipts to choose the OCR and parsing approach. The final reserved test is a separate measure; no claim of perfect extraction is made.

## What the results mean

The upgrade recovers far more real-receipt amounts, but **32 of the 161 annotated values were still missed or mismatched**, and there were 10 false positives. Review remains necessary. Some original CORD store/payment details are deliberately redacted; missing information is not inferred. Passed arithmetic is not proof of perfect text transcription.

Menu descriptions stay in the source language. Quantities and unit prices remain empty when not observed. English/Bahasa options change field labels. The application does not claim to translate every receipt line into English.

The original invoice, receipt, bank-statement, financial-report and multipage demo checks also pass with status OK after preserving the general document OCR path.

Reproduction, dependencies, licensing and model behavior: [Indonesian extraction guide](../INDONESIAN_EXTRACTION.md). Historical pilot results remain in [the earlier real receipt experiment](REAL_RECEIPTS.md).
