"""Package only the selected inference checkpoint, preserving source/license and hashes."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='artifacts/finance-analyzer-model.zip');args=parser.parse_args()
    selection=json.loads((ROOT/'run/preferred_model.json').read_text(encoding='utf-8-sig'))
    model=(ROOT/selection['model_path']).resolve()
    if not model.is_relative_to((ROOT/'models').resolve()):raise ValueError('Selected model must be under this project models directory')
    required=['config.json','model.safetensors','preprocessor_config.json','tokenizer_config.json','tokenizer.json','training_run.json','validation_results.json','test_results.json']
    if any(not (model/name).exists() for name in required):raise ValueError('Selected model is incomplete')
    files=[p for p in model.iterdir() if p.is_file() and p.suffix in ('.json','.txt','.safetensors','.md')]
    manifest={'model_path':selection['model_path'],'selection':selection,'license':'Base model: CC-BY-NC-SA-4.0; https://huggingface.co/microsoft/layoutlmv3-base',
        'scope':'Academic inference checkpoint; synthetic training/evaluation does not establish real-document accuracy',
        'files':{str(p.relative_to(ROOT)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}}
    target=ROOT/args.out;target.parent.mkdir(exist_ok=True);temporary=target.with_suffix('.partial.zip')
    with ZipFile(temporary,'w',ZIP_DEFLATED,compresslevel=1) as archive:
        for path in files:archive.write(path,path.relative_to(ROOT).as_posix())
        archive.writestr('MODEL_PACKAGE_MANIFEST.json',json.dumps(manifest,indent=2))
        archive.writestr('MODEL_TRANSFER_README.txt','Extract into the project root, preserving models/.\nRun scripts/start.ps1 -Mode token -ModelPath '+selection['model_path']+' -UseGpu\nOmit -UseGpu for CPU. Install dependencies first. Stop existing services before restarting.\nBase model license: CC-BY-NC-SA-4.0. This is a synthetic-trained academic model, not real-world validation.\n')
    with ZipFile(temporary) as archive:
        if archive.testzip() is not None:raise ValueError('Model ZIP integrity failed')
    temporary.replace(target)
    (ROOT/'reports/model_package_manifest.json').write_text(json.dumps(manifest,indent=2))
    target.with_suffix('.zip.sha256').write_text(digest(target)+'  '+target.name+'\n')
    print(f'Packaged selected model: {target} ({target.stat().st_size/1024**2:.1f} MB)',flush=True)

if __name__=='__main__':main()
