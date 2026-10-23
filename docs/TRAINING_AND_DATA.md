# Datasets, training and evaluation

## Local data and what the numbers mean

| Corpus | Local folder | Split | Intended role |
|---|---|---|---|
| Generated Indian GST invoices | `data/training_indian_invoices` | 700 / 150 / 150 | Exact word-box/BIO training and held-out synthetic evaluation |
| External Kirana invoices | `data/kirana_external` | 405 / 45 / 50 | Additional synthetic layouts; not mixed into the current training run |
| CORD sample | `data/cord_v2_sample` | 2 / 2 / 2 | Real Indonesian receipt ingestion examples; not a full CORD benchmark |

The generated set has 1,000 fictional invoices with 14 labelled fields, 29 BIO/O labels, normalized boxes, financial ground truth, relation annotations and SHA-256 hashes. Training layouts use templates 0-5, validation template 6, test template 7. Mild image variation preserves renderer coordinates. There are no Hindi training labels.

The external [Kirana publisher](https://huggingface.co/datasets/build-small-hackathon/kirana-invoice-train-data) marks its 500 invoices CC0-1.0 and fully synthetic. The publisher's 50 test examples remain test; a seeded 45-example validation set comes only from publisher training. Original financial JSON and image hashes are retained. These files lack verified token/BIO annotations. A visual training-image spot-check found displayed rates/amounts rounded relative to JSON. Read `reports/EXTERNAL_DATA_AUDIT.md` before exact row evaluation.

The [CORD release](https://github.com/clovaai/cord) is CC-BY-4.0 receipt data from Indonesia. The local six-image sample cannot support a meaningful benchmark. Its currency and partial schema are preserved; no Indian GST fields are fabricated.

## Step 1: validate or generate data

```powershell
.\backend\venv\Scripts\python.exe scripts/validate_dataset.py
```

This verifies the generated set's image hashes, split membership, label/box integrity, financial consistency and GSTIN/PAN checks. It is not a general validator for arbitrary external schemas.

To generate another set without overwriting the current one:

```powershell
.\backend\venv\Scripts\python.exe data/build_training_dataset.py --n 1000 --out data/my_training_set --seed 99
.\backend\venv\Scripts\python.exe scripts/validate_dataset.py --data data/my_training_set --output reports/my_data_validation.json
```

Import another external copy only into a new destination:

```powershell
.\backend\venv\Scripts\python.exe scripts/download_kirana.py --out data/kirana_new
```

## Step 2: verify GPU setup

This laptop has an NVIDIA RTX 3050 with 4 GB memory. CUDA training uses an isolated environment so the CPU backend remains available.

```powershell
.\scripts\setup_gpu.ps1
.\.gpu-venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

The setup uses the [official PyTorch 2.3.1 CUDA 12.1 wheel](https://pytorch.org/get-started/previous-versions/). GPU availability depends on the installed driver. Do not reinstall while the current training job is running.

## Step 3: train

For a new run, choose a new output directory:

```powershell
.\scripts\train_gpu.ps1 -Output models/layoutlmv3-next -Epochs 3 -TargetValidationF1 0.99
```

The wrapper warm-starts from the preserved initial invoice baseline when present; otherwise it uses Microsoft's base model. It uses all 700 original training examples, batch size 1, mixed precision, 256-token word-aligned windows, four CPU threads and encoder checkpointing. Windows include every source word; an oversized single word fails explicitly rather than silently dropping labels. LayoutLMv3's Transformers 4.42 compatibility adapter enables its encoder checkpointing directly.

The current `models/layoutlmv3-gpu-v2` run has a maximum of three epochs. Its 0.99 synthetic validation-F1 stopping target was declared before the first validation pass. If reached, a complete checkpoint can be finalized early. Actual epochs, updates and stopping reason are recorded. A low training loss alone is not a reason to claim completion or high real-world accuracy.

Validation chooses checkpoints; the test split is evaluated after selection. A bounded 60-step baseline and a full-data run are different training budgets. Earlier baseline scores on 20 examples are historical, not a matched comparison with a 150-example evaluation. The final report includes a full-split baseline reevaluation when available.

## Step 4: resume an interrupted run

Do not start another trainer while one is active. If an incomplete run stopped because Windows restarted, find its most recent complete checkpoint:

```powershell
$checkpoint = Get-ChildItem models/layoutlmv3-gpu-v2 -Directory -Filter 'checkpoint-*' | Sort-Object { [int]($_.Name -replace 'checkpoint-','') } | Select-Object -Last 1
$checkpoint.FullName
```

Confirm that it contains `trainer_state.json`, `model.safetensors`, optimizer and scheduler state. Then, for this original run:

```powershell
.\.gpu-venv\Scripts\python.exe -u notebooks/finetune_layoutlmv3.py --data_dir data/training_indian_invoices --model_name models/layoutlmv3-indian-invoices --output_dir models/layoutlmv3-gpu-v2 --epochs 3 --batch_size 1 --max_length 256 --gradient_checkpointing --cpu_threads 4 --target_validation_f1 0.99 --resume_from_checkpoint $checkpoint.FullName
```

Keep the same dataset, label mapping and training settings. Run `scripts/finish_upgrade.ps1` in another PowerShell only if no completion worker is already active. A completed run should be preserved; use a new output folder for new experiments.

## Step 5: evaluate and select

Evaluate a saved checkpoint without updating its weights:

```powershell
.\.gpu-venv\Scripts\python.exe notebooks/finetune_layoutlmv3.py --data_dir data/training_indian_invoices --model_name models/layoutlmv3-gpu-v2 --output_dir reports/manual_model_evaluation --evaluate_only --max_length 256 --batch_size 1 --cpu_threads 4
```

Before comparison, reevaluate the preserved baseline on the same 150-example validation/test splits (the completion worker does this):

```powershell
.\.gpu-venv\Scripts\python.exe notebooks/finetune_layoutlmv3.py --data_dir data/training_indian_invoices --model_name models/layoutlmv3-indian-invoices --output_dir reports/baseline_full_evaluation --evaluate_only --max_length 256 --batch_size 1 --cpu_threads 4
```

Select using validation and restart:

```powershell
.\backend\venv\Scripts\python.exe scripts/select_model.py --candidate models/layoutlmv3-gpu-v2
.\scripts\stop.ps1
.\scripts\start.ps1 -Mode token -UseGpu
```

The completion workflow does this after training, along with matched-slice mode comparison and live verification. Do not run GPU evaluation concurrently with GPU training on this 4 GB device.

## Step 6: compare actual extraction modes

```powershell
.\.gpu-venv\Scripts\python.exe scripts/compare_modes.py --model models/layoutlmv3-gpu-v2 --offset 20 --limit 10 --out reports/v2_comparison
```

This runs OCR-rules, model-only fields and combined extraction on the same ten reserved synthetic test documents. All modes share geometry-based table extraction. Model-only uses threshold zero to measure raw model candidates, not a deployment recommendation. Source counts identify model vs rule contributions. Latency depends on load and cold caches.

Do not tune rules or thresholds against this reserved slice after observing results. Earlier first-ten synthetic tests used for parser debugging are development checks, not untouched test evidence.

| Metric | Measures | Does not establish |
|---|---|---|
| BIO entity F1 | Exact labelled spans using supplied words/boxes | OCR quality or final invoice accuracy |
| Pipeline field F1 | Final first-page field values after OCR and fallbacks | Standalone neural-model accuracy |
| Exact row F1 | Complete row matches from shared table parser | Neural table structure or GriTS performance |
| Relation candidate F1 | Supplied-span candidate links | End-to-end OCR relation benchmark |
| Functional tests | Expected behavior on specified cases | Real-world accuracy across vendors |

## Step 7: grow a reviewed real-document training set

1. Obtain permission to use the documents and redact sensitive details as appropriate.
2. Reserve entire vendors/layouts for independent validation/test before annotation.
3. Upload training documents, inspect every field, correct and save.
4. Explicitly approve each eligible page for training. Reserved evaluation records are blocked by known invoice ID/image hash.
5. Export to a new directory:

```powershell
.\backend\venv\Scripts\python.exe scripts/export_reviewed_dataset.py --out data/reviewed_training_v1
```

6. Read `pending_alignment.json`. A corrected value absent from OCR tokens cannot become a reliable token label until a human fixes token-level annotations.
7. Use the aligned train-only supplement for a new run:

```powershell
.\.gpu-venv\Scripts\python.exe notebooks/finetune_layoutlmv3.py --data_dir data/training_indian_invoices --reviewed_data data/reviewed_training_v1 --model_name models/layoutlmv3-gpu-v2 --output_dir models/layoutlmv3-reviewed-v1 --epochs 3 --batch_size 1 --max_length 256 --gradient_checkpointing --cpu_threads 4
```

8. Evaluate independently on the reserved real set. Do not describe synthetic validation as real-document validation.

The trainer requires `annotations.jsonl` by default. `--allow_weak_labels` explicitly enables an experimental OCR/text-matched fallback when annotations are absent; those are weak labels, not human ground truth. It is not used in the current run. Approval and matching remain partial automation, not a substitute for a manual annotation audit.

## Training elsewhere and model transfer

`notebooks/train_on_colab.ipynb` provides an optional GPU workflow. Hosted execution requires your Colab account; local syntax validation is not hosted execution. Keep the original baseline intact when importing a new checkpoint, then point `-ModelPath` at the new folder or select it explicitly.

LayoutLMv3's [model card](https://huggingface.co/microsoft/layoutlmv3-base) specifies CC-BY-NC-SA-4.0. Preserve its usage conditions and model/dataset attribution. Source packaging excludes private reviewed data unless explicitly requested with `--include_reviewed`.

## Inspect the training history

`reports/gpu_training_history.csv` records available checkpoint logs plus captured process updates. `reports/gpu_training_curve.pdf` and `.svg` show training loss on a log scale and validation entity F1. Missing log entries are not reconstructed. Regenerate them with `backend/venv/Scripts/python.exe scripts/export_training_history.py`. Test scores are not used as a training curve or stopping signal.


## Operating-mode validation

A higher renderer-token BIO F1 did not make the combined pipeline outperform OCR rules. On the same 20 validation documents, OCR field F1 was 0.923 and combined mode was 0.732. OCR was selected as the recommended mode, then evaluated without tuning on a separate 20-document test slice (offset 50): field F1 0.953 and field accuracy 0.932. The earlier ten-document diagnostic comparison motivated checking operating modes and should not be described as an untouched mode-selection test. No extraction rules or model weights were changed for this choice. The trained model remains available for research and a separately verified live GPU demonstration.

## Real CORD receipt pilot

The corrected real-data importer, 60-image subset, actual OCR evaluation and completed separate classifier-head training pilot are documented in [the real-data guide](REAL_DATA.md). Use that guide instead of the legacy six-image CORD import for new experiments.
