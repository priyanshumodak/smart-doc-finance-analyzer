"""Select a finished checkpoint using validation F1 only; never select using test scores."""
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate',default='models/layoutlmv3-gpu-v2')
    parser.add_argument('--baseline',default='models/layoutlmv3-indian-invoices')
    parser.add_argument('--baseline_validation',default='reports/baseline_full_evaluation/validation_results.json')
    args=parser.parse_args()
    candidate=ROOT/args.candidate
    baseline=ROOT/args.baseline
    run=read(candidate/'training_run.json')
    if run.get('completed_optimizer_steps',0)<=0 or not (candidate/'model.safetensors').exists():
        raise ValueError('Candidate training has not finished')
    baseline_metrics=ROOT/args.baseline_validation
    if not baseline_metrics.exists():
        raise ValueError('Evaluate the baseline on the same full validation split first; see docs/TRAINING_AND_DATA.md')
    candidate_count=run.get('split_counts',{}).get('validation')
    baseline_run=read(baseline_metrics.parent/'training_run.json')
    baseline_count=baseline_run.get('split_counts',{}).get('validation')
    if candidate_count!=baseline_count:
        raise ValueError('Validation sizes differ; evaluate both models on the same split')
    current=read(baseline_metrics)['validation_f1']
    proposed=read(candidate/'validation_results.json')['validation_f1']
    selected=args.candidate if proposed>=current else args.baseline
    record={'model_path':selected,'baseline_validation_f1':current,'candidate_validation_f1':proposed,
            'validation_examples':candidate_count,'baseline_validation_source':str(baseline_metrics.relative_to(ROOT)),
            'candidate_validation_source':str((candidate/'validation_results.json').relative_to(ROOT)),
            'selection_metric':'validation entity F1 only','test_used_for_selection':False,
            'scope':'Synthetic validation; real-document generalisation remains unverified'}
    path=ROOT/'run/preferred_model.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2),flush=True)

if __name__=='__main__':
    main()
