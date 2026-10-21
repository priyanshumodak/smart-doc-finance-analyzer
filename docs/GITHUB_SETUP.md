# GitHub setup and first push

The repository keeps source, manual documentation, CI and explicitly listed fictional demos. Environments, weights, downloaded/generated data, private history, logs, local status snapshots, reports, slides and ZIPs remain on disk and are ignored.

## Push this prepared repository

An initial local commit is created after the source-only audit and clean-checkout tests pass. Create an **empty** GitHub repository (without initializing a README/license/gitignore), then run:

```powershell
git remote add origin https://github.com/YOUR-USERNAME/smart-doc-finance-analyzer.git
git push -u origin main
```

Replace YOUR-USERNAME with your account or organization. If origin is already configured, inspect `git remote -v` before changing it. No remote is guessed or pushed by the preparation step.

## Before later commits

```powershell
git status --short
git add .
python scripts/audit_repository.py
git diff --cached --stat
git commit -m "Describe the change"
git push
```

Use the project Python executable if plain `python` is not configured. The audit reads staged blobs rather than assuming the working tree is what Git will commit. It rejects blocked directories, force-added ignored files, blobs larger than 5 MiB, known credential patterns and broken relative Markdown links. It is a focused repository check, not a guarantee that every possible secret is detectable.

Never use `git add -f` for model weights, datasets, saved financial records or credentials. `.env.example` is the safe configuration template. The `sample_docs` allowlist contains only reviewed fictional fixtures; arbitrary new files in that folder are ignored.

## Reproduce locally after cloning

1. Install Python 3.11 and OCR/PDF system dependencies.
2. Run `scripts/setup.ps1`, then `scripts/start.ps1 -Mode ocr`.
3. Generate the training corpus with the command in the root README when needed. A Git clone intentionally does not include the local 1,000-image corpus, 500-image external download, weights or installed environments.
4. Train a new model or restore a complete inference model separately. Preserve model/data notices; do not treat them as application source.
5. Generate local status, reports, handbook and slides only when the required local result artifacts exist. The [public results snapshot](results/README.md) remains readable without them.

## CI

`.github/workflows/tests.yml` uses Python 3.11, CPU PyTorch, system OCR/PDF tools, the repository audit and both regression suites. It downloads dependencies but no pretrained model weights or invoice dataset. Its action versions follow the official [checkout](https://github.com/actions/checkout) and [setup-python](https://github.com/actions/setup-python) documentation. Hosted CI cannot run until the repository is pushed.

## Licensing and release files

[Third-party notices](../NOTICE.md) preserve model/dataset attribution. A blanket source-code license is not chosen on behalf of all project authors. Add the team's chosen license separately if desired.

Large source/data or model ZIPs can remain local or be shared separately under their applicable terms. Do not force them into Git history to bypass ignore rules. The generated local archives and private backups are not removed by repository preparation.


## Local preparation verification

The reviewed index contains 116 files totaling approximately 0.93 MiB; its largest file is a 116,646-byte fictional demo PDF. The staged audit passed and both regression suites passed from an isolated source-only checkout (39 backend + four dashboard tests). Python syntax, PowerShell parsing and CI YAML structure were checked locally. Hosted GitHub Actions execution remains pending the first push.
