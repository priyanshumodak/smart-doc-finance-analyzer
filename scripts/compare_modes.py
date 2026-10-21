"""Compare first-page financial fields, exact line-item rows and latency across extraction modes."""
import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from statistics import median

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.validation import money

def row_key(row):
    name=' '.join(str(row.get('description',row.get('item',''))).casefold().split())
    return (name,)+tuple(str(value.normalize()) if (value:=money(row.get(field))) is not None else '' for field in ('qty','rate','amount'))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',default='data/training_indian_invoices')
    parser.add_argument('--model',default='models/layoutlmv3-indian-invoices')
    parser.add_argument('--offset',type=int,default=20)
    parser.add_argument('--limit',type=int,default=10)
    parser.add_argument('--out',default='reports/mode_comparison')
    parser.add_argument('--reuse',action='store_true',help='Summarize existing completed runs only')
    args=parser.parse_args()
    root=Path(args.out)
    root.mkdir(parents=True,exist_ok=True)
    truth=json.loads((Path(args.data)/'test.json').read_text(encoding='utf-8-sig'))[args.offset:args.offset+args.limit]
    results={}
    for mode in ('ocr','model','token'):
        folder=root/mode
        if not args.reuse:
            subprocess.run([sys.executable,str(ROOT/'scripts/benchmark_pipeline.py'),'--data',args.data,'--mode',mode,
                            '--model',args.model,'--offset',str(args.offset),'--limit',str(args.limit),'--out',str(folder)],check=True,cwd=ROOT)
        evaluation=json.loads((folder/'evaluation.json').read_text())
        tp=fp=fn=0
        times=[]
        contributions=Counter()
        for record in truth:
            output=json.loads((folder/(Path(record['image_path']).stem+'.json')).read_text())
            times.append(output['processing_seconds'])
            actual=output['pages'][0]
            expected_rows=Counter(row_key(row) for row in record.get('line_items',[]))
            actual_rows=Counter(row_key(row) for row in actual['line_items'])
            common=sum((expected_rows&actual_rows).values())
            tp+=common
            fp+=sum(actual_rows.values())-common
            fn+=sum(expected_rows.values())-common
            contributions.update(value.get('source','unknown') for value in actual['fields'].values() if value.get('value') is not None)
        precision=tp/(tp+fp) if tp+fp else 0
        recall=tp/(tp+fn) if tp+fn else 0
        results[mode]={'fields':evaluation['micro'],'line_item_rows':{'tp':tp,'fp':fp,'fn':fn,'precision':precision,'recall':recall,
                         'f1':2*precision*recall/(precision+recall) if precision+recall else 0},
                       'median_seconds':median(times),'field_sources':dict(contributions)}
    report={'dataset':args.data,'offset':args.offset,'documents':len(truth),'model':args.model,'modes':results,
            'scope':'Same synthetic test slice across modes. Field exact match and exact full line-item row match. Table extraction remains shared geometry; not a learned table model/GriTS benchmark.'}
    (root/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (root/'comparison.csv').open('w',newline='',encoding='utf-8') as file:
        writer=csv.writer(file)
        writer.writerow(['mode','field_precision','field_recall','field_f1','field_accuracy','exact_row_f1','median_seconds'])
        for mode,row in results.items():
            writer.writerow([mode,row['fields']['precision'],row['fields']['recall'],row['fields']['f1'],row['fields']['accuracy'],row['line_item_rows']['f1'],row['median_seconds']])
    lines=['# Extraction mode comparison','','Scope: '+report['scope'],'',
           '| Mode | Field accuracy | Field F1 | Exact row F1 | Median seconds |','|---|---:|---:|---:|---:|']
    for mode,row in results.items():
        lines.append(f"| {mode} | {row['fields']['accuracy']:.3f} | {row['fields']['f1']:.3f} | {row['line_item_rows']['f1']:.3f} | {row['median_seconds']:.2f} |")
    lines.extend(['','`ocr`: labelled OCR rules. `model`: model-only field candidates with threshold zero. `token`: model plus rules and candidate checks.',
                  'Mode-level source counts are in comparison.json; combined scores must not be described as standalone model accuracy.'])
    (root/'COMPARISON.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    main()
