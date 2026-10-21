"""Read actual local artifacts and service health; optionally write the handover status."""
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]

def read(relative):
    path=ROOT/relative
    if not path.exists(): return None
    try: return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError,ValueError): return None

def collect():
    states=[]
    for path in (ROOT/'models/layoutlmv3-gpu-v2').glob('checkpoint-*/trainer_state.json'):
        state=read(path.relative_to(ROOT))
        if state: states.append(state)
    latest=max(states,key=lambda row:row.get('global_step',0)) if states else None
    health={}
    for name,url in [('api','http://127.0.0.1:8000/health'),('dashboard','http://127.0.0.1:8501/_stcore/health')]:
        try:
            with urlopen(url,timeout=5) as response:
                body=response.read().decode()
                health[name]={'reachable':True,'response':json.loads(body) if name=='api' else body}
        except Exception as exc: health[name]={'reachable':False,'error':str(exc)}
    observed=read('reports/observed_training_progress.json') or []
    validation=read('models/layoutlmv3-gpu-v2/validation_results.json')
    test=read('models/layoutlmv3-gpu-v2/test_results.json')
    run=read('models/layoutlmv3-gpu-v2/training_run.json')
    return {'generated_at':datetime.now(timezone.utc).isoformat(),'completion':read('run/upgrade_completion.json'),
        'services':health,'preferred_model':read('run/preferred_model.json'),'operating_mode':read('run/preferred_mode.json'),'training':run,
        'model_finished':bool(run and run.get('completed_optimizer_steps') and validation and test),
        'latest_observed_training_update':observed[-1] if observed else None,
        'latest_saved_checkpoint':{'step':latest['global_step'],'epoch':latest['epoch'],'best_validation_f1':latest.get('best_metric')} if latest else None,
        'validation':validation,'test':test,'regression_suites':read('reports/upgraded_tests.json'),
        'live_upload':read('reports/live_app_verification.json'),'live_multipage':read('reports/live_upgrade_verification.json'),
        'mode_comparison':read('reports/v2_comparison/comparison.json'),
        'datasets':{name:read('data/'+name+'/manifest.json') for name in ('training_indian_invoices','kirana_external','cord_v2_sample')},
        'scope':'Synthetic model/evaluation results and local functional checks. Real-document accuracy remains unverified.'}

def render(result):
    completion=result.get('completion') or {}
    lines=['# Current project status','',f"Generated: {result['generated_at']} (UTC)",'',
        'This page is generated from saved artifacts and current endpoint checks. A saved checkpoint is not proof that the full training job has completed.','',
        '| Item | State |','|---|---|',f"| Completion workflow | {completion.get('status','not recorded')} |",
        f"| Final GPU training/evaluation artifacts | {'complete' if result['model_finished'] else 'pending'} |"]
    for name,service in result['services'].items(): lines.append(f"| {name} endpoint | {'reachable' if service['reachable'] else 'unreachable'} |")
    for suite in result.get('regression_suites') or []:
        lines.append(f"| {suite['suite']} tests | {suite['tests']} {'passed' if suite['passed'] else 'FAILED'} |")
    operating=result.get('operating_mode') or {}
    lines+=['',f"Recommended operating mode: {operating.get('recommended_mode','pending validation check')}",'']
    selected=result.get('preferred_model') or {}
    lines+=['',f"Preferred model: {selected.get('model_path','not yet selected')}",'']
    if result.get('latest_observed_training_update') and not result['model_finished']:
        lines+=['Latest captured process update (a snapshot, not a live counter):','', '```json',json.dumps(result['latest_observed_training_update'],indent=2),'```','']
    if result['latest_saved_checkpoint']:
        label='Validation-selected retained checkpoint:' if result['model_finished'] else 'Latest saved checkpoint (not live step count):'
        lines+=[label,'', '```json',json.dumps(result['latest_saved_checkpoint'],indent=2),'```','']
    if result.get('validation') and result.get('test'):
        lines+=['## Final synthetic entity metrics','',f"Validation F1: {result['validation']['validation_f1']:.4f}",f"Test F1: {result['test']['test_f1']:.4f}",'']
    lines+=['## Completion record','', '```json',json.dumps(result['completion'],indent=2),'```','',
        '## Live API configuration','', '```json',json.dumps(result['services']['api'],indent=2),'```','',
        '## Evidence and next commands','',
        '- Read `reports/UPGRADE_RESULTS.md` for measured results and limitations.',
        '- Read `run/upgrade-finalization.log` for final successful packaging; earlier attempt/recovery logs remain in run/.',
        '- Run `backend/venv/Scripts/python.exe scripts/project_status.py --write` to refresh this page.',
        '- Start the recommended default with `scripts/start.ps1 -Mode ocr`; use `-Mode token -UseGpu` for the optional trained-model demonstration after stopping services.',
        '',result['scope']]
    return '\n'.join(lines)+'\n'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');args=parser.parse_args()
    result=collect()
    if args.write:
        (ROOT/'docs').mkdir(exist_ok=True);(ROOT/'reports').mkdir(exist_ok=True)
        (ROOT/'docs/STATUS.md').write_text(render(result),encoding='utf-8')
        (ROOT/'reports/project_status.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(render(result),flush=True)

if __name__=='__main__': main()
