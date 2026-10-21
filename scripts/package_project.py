"""Bundle source and optional synthetic training data, excluding environments, caches and private history."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dataset',action='store_true')
    parser.add_argument('--include_reviewed',action='store_true',help='Explicitly include local human-reviewed financial data')
    parser.add_argument('--out',default='artifacts/finance-analyzer.zip')
    args=parser.parse_args()
    target=ROOT/args.out
    target.parent.mkdir(parents=True,exist_ok=True)
    skip={'venv','.venv','.gpu-venv','__pycache__','.git','.pytest_cache','storage','run','model-cache','models','artifacts','publisher_pages'}
    files=[]
    for directory in ('backend','frontend','notebooks','scripts','tests','data','sample_docs','docs','.github'):
        def collect(folder):
            for path in folder.iterdir():
                if path.name in skip or path.suffix in ('.pyc','.sqlite3'):
                    continue
                if path.is_dir():
                    manifest=path/'manifest.json'
                    if manifest.exists() and not args.include_reviewed:
                        metadata=json.loads(manifest.read_text(encoding='utf-8-sig'))
                        if metadata.get('source')=='local reviewed documents':
                            continue
                    if path.name.startswith('reviewed_training') and not args.include_reviewed:
                        continue
                    if (path.name in ('training_indian_invoices','cord_v2_sample','synthetic_indian_invoices') or (path/'manifest.json').exists()) and not args.dataset:
                        continue
                    collect(path)
                elif path.is_file():
                    files.append(path)
        collect(ROOT/directory)
    files.extend(path for name in ('README.md','PROJECT_GUIDE.md','UPGRADE_GUIDE.md','NOTICE.md','docker-compose.yml','Dockerfile','.dockerignore','render.yaml','.env.example','.gitignore','.gitattributes','.python-version') if (path:=ROOT/name).is_file())
    files.extend(path for name in ('PROJECT_RESULTS.md','project_results.json','dataset_validation.json','demo_verification.json','training_loss.csv','live_app_verification.json') if (path:=ROOT/'reports'/name).is_file())
    files.extend(path for relative in ('reports/gpu_training_history.csv','reports/gpu_training_history_manifest.json','reports/gpu_training_curve.pdf','reports/gpu_training_curve.svg','reports/EXTERNAL_DATA_AUDIT.md','reports/UPGRADE_RESULTS.md','reports/upgrade_results.json','reports/upgraded_tests.json','reports/pdf_path_comparison.json','reports/v2_comparison/COMPARISON.md','reports/v2_comparison/comparison.json') if (path:=ROOT/relative).is_file())
    for relative in ('reports/validation_modes/selection.json','reports/validation_modes/ocr/evaluation.json','reports/validation_modes/token/evaluation.json','reports/recommended_mode_test/evaluation.json','reports/live_model_verification.json','reports/live_upgrade_verification.json','reports/live_extraction.json','reports/model_package_manifest.json','reports/presentation_manifest.json','reports/baseline_full_evaluation/validation_results.json','reports/baseline_full_evaluation/test_results.json','reports/baseline_full_evaluation/training_run.json','reports/external_kirana_ocr/evaluation.json','reports/external_kirana_token/evaluation.json','reports/v2_comparison/comparison.csv'):
        path=ROOT/relative
        if path.exists(): files.append(path)
    for artifact in ('PROJECT_HANDBOOK.pdf','PROFESSOR_PRESENTATION.pptx','PROFESSOR_PRESENTATION.pdf','DEMO_OUTPUT.json','DEMO_OUTPUT.xlsx'):
        path=ROOT/'artifacts'/artifact
        if path.exists(): files.append(path)
    temporary=target.with_suffix('.partial.zip')
    with ZipFile(temporary,'w',ZIP_DEFLATED,compresslevel=6) as bundle:
        for path in files:
            bundle.write(path,path.relative_to(ROOT).as_posix())
    temporary.replace(target)
    checksum=hashlib.sha256()
    with target.open('rb') as file:
        for chunk in iter(lambda:file.read(1024*1024),b''):
            checksum.update(chunk)
    target.with_suffix('.zip.sha256').write_text(checksum.hexdigest()+'  '+target.name+'\n')
    print(f'Packaged {len(files)} files: {target} ({target.stat().st_size/1024/1024:.1f} MB)',flush=True)

if __name__=='__main__':
    main()
