# Implementation and verification change log

## Core application

- Fixed the Streamlit OCR-ready rendering failure and added rendered-dashboard regressions.
- Preserved OCR-only, pretrained QA and locally trained token modes.
- Added native PDF words/tables with page-by-page OCR fallback and aligned source previews.
- Corrected visible CropBox extraction/origin handling; a regression verifies that hidden margins are excluded and highlight boxes contain source ink.
- Added independent field candidates, format/checksum guards, observed-value arithmetic ranking and explicit conflicts.
- Improved wrapped table rows, header aliases, HSN/discount/tax columns and supported continuation tables.
- Added conservative multipage grouping, combined validation, page provenance and merged Excel sheets.
- Added editable bank transactions with recalculated balance checks.
- Retained originals after human corrections and invalidated stale training approvals.
- Added explicit reviewed-page approval, word alignment, pending annotations and reserved-evaluation guards.
- Added active checkpoint/device diagnostics for demonstrable model deployment.

## Data and training

- Generated and integrity-checked 1,000 fictional Indian GST invoices with exact token/box/BIO labels and 700/150/150 splits.
- Preserved the initial bounded CPU model as a historical integration baseline.
- Created an isolated CUDA environment and started full-data LayoutLMv3 fine-tuning with a predeclared validation stopping rule.
- Added encoder-checkpointing compatibility and word-aligned contexts.
- Imported 500 CC0 external synthetic Kirana invoices, repaired both publisher annotation schemas, retained raw JSON/hashes and recorded visible rounding limitations.
- Required explicit weak-label opt-in for unannotated training experiments.
- Added matched-split baseline evaluation, same-document extraction-mode comparisons and validation-only selection.

## Documentation and handover

- Added setup/operations, complete UI walkthrough, training/resume, dataset provenance, architecture/API, professor demo and viva guides.
- Added generated artifact-based status, a printable handbook and reproducible packaging.
- See `reports/UPGRADE_RESULTS.md`, `reports/upgraded_tests.json`, `reports/test_logs/` and `docs/STATUS.md` for actual results and completion. This change log does not mark pending training as finished.

## Remaining scope

Permission-cleared real Indian invoice annotation and independent evaluation; trained table-structure recognition; robust handwriting/Hindi evaluation; authentication and production deployment. These are not silently claimed as implemented or evaluated.


## Completion recovery

The three-epoch run and full-split baseline evaluation finished. A post-training policy JSON reader failed on a Windows encoding marker. The reader was fixed to use UTF-8/BOM-compatible decoding, completion gained a resume option, and selection/deployment/packaging resumed without rerunning training or the completed baseline evaluation. Final completion is recorded in `run/upgrade_completion.json`.


## Runtime verification

The resumed job completed comparisons but its initial live GPU upload exited inside NVIDIA's nvcuda64.dll (Windows event 1000, exception 0xc0000409). Stable OCR service was restored while testing startup-thread model initialization. GPU training/standalone inference and HTTP deployment are verified separately; see final live reports for the verified operating configuration.


Main-thread model initialization resolved the observed live CUDA first-upload failure; the verified response records model layoutlmv3-gpu-v2, device cuda:0 and 14 accepted model fields. A startup-order regression was added. Validation-mode comparison (20 matching synthetic documents) favored OCR rules, field F1 0.923 versus combined mode 0.732, so the recommended default remains OCR. Model weights and extraction rules were not tuned after observing the diagnostic test slice.
