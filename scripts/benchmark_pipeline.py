"""Run honest end-to-end OCR/model field evaluation on a selected held-out split."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',default='data/training_indian_invoices')
    parser.add_argument('--split',default='test',choices=['train','validation','test'])
    parser.add_argument('--limit',type=int,default=20)
    parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--mode',default='ocr',choices=['ocr','token','auto','model'])
    parser.add_argument('--locale',default='auto',choices=['auto','id-ID','en-IN'])
    parser.add_argument('--text_mode',choices=['auto','ocr'],default='auto')
    parser.add_argument('--model',default='models/layoutlmv3-indian-invoices')
    parser.add_argument('--out',default='reports/ocr_test')
    args=parser.parse_args()
    os.environ['TEXT_EXTRACTION_MODE']=args.text_mode
    os.environ['CANDIDATE_POLICY']='model_only' if args.mode=='model' else 'combined'
    if args.mode=='model':
        os.environ['TOKEN_MIN_CONFIDENCE']='0'
    if args.mode in ('token','model'):
        os.environ['TOKEN_MODEL_PATH']=str(Path(args.model).resolve())
        os.environ['EXTRACTION_MODE']='auto'
    else:
        os.environ['EXTRACTION_MODE']=args.mode
        os.environ.pop('TOKEN_MODEL_PATH',None)
    folder=Path(args.out)
    folder.mkdir(parents=True,exist_ok=True)
    os.environ['DATABASE_PATH']=str(folder/'results.sqlite3')
    os.environ['OMP_NUM_THREADS']='4'
    from backend.app import process
    from scripts.evaluate import evaluate
    root=Path(args.data)
    truth=json.loads((root/f'{args.split}.json').read_text(encoding='utf-8-sig'))
    selected=truth[args.offset:args.offset+args.limit] if args.limit else truth[args.offset:]
    if not selected:
        raise ValueError('Selected benchmark slice is empty')
    predictions=[]
    started=time.perf_counter()
    for index,record in enumerate(selected,1):
        path=root/record['image_path']
        result=process(path.read_bytes(),path.name,args.locale)
        predictions.append(result)
        (folder/f'{path.stem}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'{index}/{len(selected)}: {path.name}: {result["status"]}',flush=True)
    report=evaluate(selected,predictions)
    manifest_path=root/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig')) if manifest_path.exists() else {}
    report.update({'mode':args.mode,'split':args.split,'limit':args.limit,'offset':args.offset,'seconds':round(time.perf_counter()-started,2),
                   'dataset':str(root),'locale':args.locale,'text_mode':args.text_mode,'candidate_policy':os.environ['CANDIDATE_POLICY'],'dataset_metadata':{key:manifest.get(key) for key in ('name','source','license','source_revision','real_documents')},
                   'scope':'End-to-end first-page fields after actual OCR and extraction; explicit annotation masks apply. Real and synthetic datasets are reported separately. Not token BIO F1.'})
    (folder/'evaluation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report['micro'],indent=2),flush=True)

if __name__=='__main__':
    main()
