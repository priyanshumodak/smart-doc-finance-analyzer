"""Summarize actual local artifacts without inventing missing metrics."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def read(relative):
    path=ROOT/relative
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else None

def main():
    dataset=read('reports/dataset_validation.json')
    run=read('models/layoutlmv3-indian-invoices/training_run.json')
    validation=read('models/layoutlmv3-indian-invoices/validation_results.json')
    test=read('models/layoutlmv3-indian-invoices/test_results.json')
    relations=read('models/spatial-relations.json')
    pipeline=read('reports/ocr_test_final/evaluation.json')
    demos=read('reports/demo_verification.json')
    live=read('reports/live_app_verification.json')
    trained_pipeline=read('reports/token_test/evaluation.json')
    status='complete' if all(item is not None for item in (dataset,run,validation,test,relations,pipeline,demos)) else 'incomplete'
    result={'status':status,'dataset':dataset,'training':run,'validation':validation,'test':test,
            'relation_candidate_metrics':{key:relations[key] for key in ('scope','validation','test')} if relations else None,
            'ocr_pipeline_development_metrics':pipeline,'token_pipeline_metrics':trained_pipeline,'demo_verification':demos,'live_app_verification':live,
            'limitations':['Synthetic data and bounded training run; not production validation',
                           'First ten pipeline examples were used for parser development',
                           'CORD sample imported; full CORD/FUNSD benchmark not run',
                           'Table structure remains heuristic; spatial relation classifier is a small baseline',
                           'Colab notebook syntax-checked locally, not executed in a hosted account',
                           'Undertrained token model can have zero fields above the confidence threshold; pipeline scores include OCR/rule fallbacks']}
    reports=ROOT/'reports'
    reports.mkdir(exist_ok=True)
    (reports/'project_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# Local project results','',f'Artifact status: {status}','',
           'This report summarizes actual generated artifacts. Read the metric scopes before using numbers in a project report.','']
    if dataset:
        lines.extend([f"Generated dataset: {dataset['documents']} images; splits {dataset['splits']}; validation {dataset['status']}.",''])
    if run:
        lines.extend([f"LayoutLMv3 run: {run['train_mode']}; max steps {run['max_steps']}; subset counts {run['split_counts']}; CUDA {run['cuda']}.",''])
    for name,metrics in [('Validation entity metrics',validation),('Test entity metrics',test)]:
        lines.extend(['## '+name,'','```json',json.dumps(metrics,indent=2) if metrics else 'Not available','```',''])
    if relations:
        lines.extend(['## Spatial relation candidate classifier','',relations['scope'],'',
                      '```json',json.dumps({key:relations[key] for key in ('validation','test')},indent=2),'```',''])
    if pipeline:
        lines.extend(['## OCR pipeline development check','',pipeline.get('evaluation_role','Synthetic development check'),'',
                      '```json',json.dumps(pipeline['micro'],indent=2),'```',''])
    if trained_pipeline:
        lines.extend(['## Trained-model pipeline check','',trained_pipeline['scope'],'',
                      '```json',json.dumps(trained_pipeline['micro'],indent=2),'```',''])
    if live:
        lines.extend(['## Live application integration','','Model execution and confidence gating:','',
                      '`json',json.dumps(live,indent=2),'`','',
                      'Pipeline field scores include OCR/rule fallbacks and are not standalone token model accuracy.',''])
    if demos:
        lines.extend(['## Real OCR demo checks','','| File | Pages | Status |','|---|---:|---|'])
        lines.extend(f"| {row['filename']} | {row['pages']} | {row['status']} |" for row in demos)
    lines.extend(['','## Limits','']+['- '+item for item in result['limitations']])
    (reports/'PROJECT_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Wrote reports/PROJECT_RESULTS.md and project_results.json. Status:',status,flush=True)

if __name__=='__main__':
    main()
