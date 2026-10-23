# Real CORD-v2 receipt experiment

Date: 23 October 2026. Dataset: 60 real Indonesian receipt images, preserving the publisher's original split assignments (20/20/20). License CC-BY-4.0. Full setup and limitations: [real-data guide](../REAL_DATA.md).

Source: [CORD-v2 by Clova AI/NAVER](https://huggingface.co/datasets/naver-clova-ix/cord-v2), observed revision `7f0115a4b758a71d6473b8d085751692da2fef98`. Viewer JPEG derivatives, canonical gt_parse values and original annotations are retained with hashes. This first-N subset is not a representative sample of all receipt layouts.

Only subtotal, tax and total are mapped. Other fields are excluded using explicit annotation masks. IDR formatting is normalized separately from Indian numeric conventions. No synthetic invoices are included in these results.

| End-to-end method | Documents | Annotated values | TP | FP | FN | Field F1 | Field accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Actual OCR + existing rules | 20 | 40 | 7 | 3 | 33 | 28.00% | 17.50% |
| Actual OCR + real-data pilot + rules | 20 | 40 | 7 | 12 | 33 | 23.73% | 17.50% |

All 20 documents required review for both methods. The pilot was not promoted; the hosted application retains OCR mode. These results show domain limitations rather than an accuracy improvement.

The separate one-epoch GPU pilot froze the LayoutLMv3 backbone and trained only the classifier head on the 20 official training-subset examples, selecting its checkpoint on the 20 validation examples. It completed 20 optimizer steps. Using supplied words and boxes (not OCR output), validation BIO/entity F1 was 21.05% and test BIO/entity F1 was 33.71%. Those scores are a different measurement from the end-to-end field table.

Three real training-split JPEGs are included for the website demonstration with [attribution](../../sample_docs/real_receipts/ATTRIBUTION.md). Reference amounts displayed in the app are comparison labels, not extraction inputs. Held-out test receipts are not shipped as demo samples.

Raw images, model weights and detailed generated reports remain local under ignored data/model/report paths. The older six-image CORD import has a legacy label mapping and must not be used as the corrected benchmark.
