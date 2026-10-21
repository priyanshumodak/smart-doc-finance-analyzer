"""Report second-round improvements using completed artifacts only."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def read(relative):
    path=ROOT/relative
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else None

def main():
    from export_training_history import export
    history=export()
    baseline=read('models/layoutlmv3-indian-invoices/test_results.json')
    baseline_full_validation=read('reports/baseline_full_evaluation/validation_results.json')
    baseline_full_test=read('reports/baseline_full_evaluation/test_results.json')
    external={mode:read(f'reports/external_kirana_{mode}/evaluation.json') for mode in ('ocr','token')}
    validation=read('models/layoutlmv3-gpu-v2/validation_results.json')
    test=read('models/layoutlmv3-gpu-v2/test_results.json')
    run=read('models/layoutlmv3-gpu-v2/training_run.json')
    tests=read('reports/upgraded_tests.json')
    timing=read('reports/pdf_path_comparison.json')
    live=read('reports/live_upgrade_verification.json')
    live_model=read('reports/live_model_verification.json')
    comparison=read('reports/v2_comparison/comparison.json')
    selected=read('run/preferred_model.json')
    operating=read('run/preferred_mode.json')
    mode_test=read('reports/recommended_mode_test/evaluation.json')
    states=list((ROOT/'models/layoutlmv3-gpu-v2').glob('checkpoint-*/trainer_state.json'))
    latest=read(str(max(states,key=lambda p:p.stat().st_mtime).relative_to(ROOT))) if states else None
    finished=bool(run and run.get('completed_optimizer_steps') and validation and test)
    result={'gpu_training_finished':finished,'gpu_training':run,'latest_checkpoint_validation':latest and {'step':latest['global_step'],'epoch':latest['epoch'],'f1':latest['best_metric']},'validation':validation,'test':test,
            'original_baseline_test':baseline,'matched_full_baseline_validation':baseline_full_validation,'matched_full_baseline_test':baseline_full_test,'external_synthetic_validation':external,'regression_suites':tests,'training_history':history,'pdf_path_comparison':timing,
            'live_verification':live,'live_model_integration':live_model,'mode_comparison':comparison,'selection':selected,'operating_mode_selection':operating,'recommended_mode_test':mode_test,
            'scope':'Synthetic invoice training/evaluation and local functional demos. Not a real-world Indian invoice benchmark.',
            'remaining':['Permission-cleared real invoice annotation and independent real-document evaluation',
                         'Learned table-structure recognition and broader handwriting/Hindi evaluation']}
    (ROOT/'reports/upgrade_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# Upgrade results','',result['scope'],'',
           '## Implemented','',
           '- Native PDF words and tables with per-page OCR fallback; visible-crop coordinates stay aligned and hidden crop margins are excluded.',
           '- Independent model/rule candidates, format checks, arithmetic-supported selection and conflict reporting.',
           '- Real-page field highlights and persistent processed previews.',
           '- Conservative multipage grouping and document-level reconciliation/export.',
           '- Wrapped table descriptions, HSN/discount/tax columns and simple-table suffix fallback.',
           '- Editable bank transactions and approved train-only correction export.',
           '- Isolated CUDA training/inference with word-aligned windows and LayoutLMv3 encoder checkpointing.','',
           '## Tests','','```json',json.dumps(tests,indent=2),'```','',
           '## Training','','Completed: '+str(finished),'','```json',json.dumps(run,indent=2),'```','',
           '## Measured entity metrics','','| Run | Evaluation documents per split | Validation F1 | Test F1 |','|---|---:|---:|---:|',
           f"| Historical 60-step CPU baseline | 20 | 0.415 | {baseline['test_f1']:.3f} |" if baseline else '| Historical baseline | 20 | unavailable | unavailable |',
           f"| Same baseline, full-split reevaluation | 150 | {baseline_full_validation['validation_f1']:.3f} | {baseline_full_test['test_f1']:.3f} |" if baseline_full_validation and baseline_full_test else '| Full-split baseline reevaluation | 150 | pending | pending |',
           f"| Full-data CUDA run | 150 | {validation['validation_f1']:.3f} | {test['test_f1']:.3f} |" if validation and test else '| CUDA run | 150 | pending | pending |','']
    lines.extend(['Historical small-subset metrics and full-split metrics are different evaluation sizes. Use the full-split baseline row for a matched comparison.',''])
    if latest and not finished:
        lines.extend(['Latest complete checkpoint: step '+str(latest['global_step'])+', epoch '+str(latest['epoch'])+', validation F1 '+str(latest['best_metric'])+'. Training continues; final test metrics are pending.',''])
    if timing:
        lines.extend(['## PDF path timing','','Generated cases in OCR-rule mode, without neural inference; cold/warm caches and system load affect timings. Live model-mode latency differs.','',
                      '| File | Text path | Seconds | Status |','|---|---|---:|---|'])
        lines.extend(f"| {row['file']} | {row['text_mode']} | {row['seconds']:.2f} | {row['status']} |" for row in timing['runs'])
    if comparison:
        lines.extend(['','## Same-document mode comparison','',comparison['scope'],'',
                      '| Mode | Field F1 | Field accuracy | Exact row F1 | Median seconds |','|---|---:|---:|---:|---:|'])
        for mode,row in comparison['modes'].items():
            lines.append(f"| {mode} | {row['fields']['f1']:.3f} | {row['fields']['accuracy']:.3f} | {row['line_item_rows']['f1']:.3f} | {row['median_seconds']:.2f} |")
    if operating:
        lines.extend(['','## Recommended operating mode','',f"Recommended: **{operating['recommended_mode']}**; selected by final-field F1 on {operating['validation_documents']} matching validation examples. No weights or extraction rules changed. The earlier diagnostic test comparison motivated this validation check; operating-mode choice did not use the new reserved test slice.",'', '| Mode | Validation field F1 | Validation field accuracy |','|---|---:|---:|'])
        for name,row in operating['scores'].items():
            lines.append(f"| {name} | {row['f1']:.3f} | {row['accuracy']:.3f} |")
        if mode_test:
            lines.extend(['',f"After mode selection: {mode_test['documents']} separate reserved synthetic test documents, offset {mode_test['offset']}, field F1 {mode_test['micro']['f1']:.3f}, accuracy {mode_test['micro']['accuracy']:.3f}. No tuning on this result.",''])
    if any(external.values()):
        lines.extend(['','## External synthetic layout check','','Five external Kirana validation documents, partial publisher field masks, no training on this corpus. Printed/JSON rounding limitations apply. This is a small domain-shift diagnostic, not a real-document benchmark.','', '| Mode | Documents | Field F1 | Field accuracy |','|---|---:|---:|---:|'])
        for mode,row in external.items():
            if row:
                lines.append(f"| {mode} | {row['documents']} | {row['micro']['f1']:.3f} | {row['micro']['accuracy']:.3f} |")
    lines.extend(['','## Live application','','The final app uses the validation-recommended operating mode. The trained GPU model was also exercised through the actual HTTP API after startup-thread initialization.','', '```json',json.dumps(live,indent=2),'```','', 'GPU model integration (separate from the recommended default):','', '```json',json.dumps(live_model,indent=2),'```','',
                  '## Remaining scope','']+['- '+item for item in result['remaining']])
    (ROOT/'reports/UPGRADE_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Wrote upgrade report. GPU training complete:',finished,flush=True)

if __name__=='__main__':
    main()
