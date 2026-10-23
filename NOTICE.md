# Third-party notices

Model and dataset terms are separate from the application's source. This repository does not bundle pretrained/fine-tuned weights or downloaded corpora and does not relicense third-party assets.

- Microsoft LayoutLMv3 base model: CC-BY-NC-SA-4.0, per https://huggingface.co/microsoft/layoutlmv3-base. Preserve its attribution and academic/noncommercial conditions when transferring derived weights.
- External synthetic Kirana invoices: publisher marks CC0-1.0 at https://huggingface.co/datasets/build-small-hackathon/kirana-invoice-train-data. Downloaded copies remain local.
- CORD: retain the original CC-BY-4.0 notice and attribution from https://github.com/clovaai/cord.
- The included sample_docs files are fictional project-generated demonstration records; they are not real customer invoices.
- Tesseract, pdfplumber, PyTorch, Transformers and other dependencies retain their respective licenses.

No blanket open-source license has been assigned to the team's original application code in this preparation step. The project owners can add their chosen source license separately; third-party model/data terms still apply.

Three real CORD-v2 training-split receipt JPEG derivatives are redistributed under CC-BY-4.0 in `sample_docs/real_receipts`; attribution, license text, source indices and hashes are included there. Copyright and dataset attribution remain with the original authors/Clova AI/NAVER.

The Indonesian receipt pipeline uses RapidOCR/PP-OCRv6 and ONNX Runtime from installed packages. RapidOCR and PaddleOCR publish Apache-2.0 licenses; retain their packaged licenses/notices. Sources: https://github.com/RapidAI/RapidOCR and https://github.com/PaddlePaddle/PaddleOCR . The compact receipt-line classifier is trained from CORD-v2 (CC-BY-4.0); see its card under `backend/assets`. No original upstream neural weights are copied into this Git repository.
