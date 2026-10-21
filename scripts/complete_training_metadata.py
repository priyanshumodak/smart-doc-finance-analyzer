"""Attach saved checkpoint provenance to a completed run without changing weights."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    model=ROOT/'models/layoutlmv3-gpu-v2'
    metadata=json.loads((model/'training_run.json').read_text(encoding='utf-8-sig'))
    if not metadata.get('completed_optimizer_steps') or not (model/'test_results.json').exists():
        raise ValueError('Training and held-out evaluation must finish before metadata finalization')
    policy=json.loads((ROOT/'run/training_policy.json').read_text(encoding='utf-8-sig'))
    states=[json.loads(p.read_text(encoding='utf-8-sig')) for p in model.glob('checkpoint-*/trainer_state.json')]
    if not states:raise ValueError('Saved checkpoint provenance unavailable')
    state=max(states,key=lambda s:s['global_step'])
    metadata.setdefault('selected_checkpoint',state.get('best_model_checkpoint'))
    selected=Path(metadata.get('selected_checkpoint') or state.get('best_model_checkpoint',''))
    selected_state=selected/'trainer_state.json'
    if selected_state.exists():
        selected_record=json.loads(selected_state.read_text(encoding='utf-8-sig'))
        metadata['selected_checkpoint_optimizer_step']=selected_record['global_step']
        metadata['selected_checkpoint_epoch']=selected_record['epoch']
    metadata.setdefault('best_validation_f1',state.get('best_metric'))
    metadata.setdefault('target_validation_f1',policy['target_validation_f1'])
    metadata.setdefault('stop_reason','Configured maximum training epochs completed' if metadata['completed_epochs']>=policy['maximum_epochs'] else 'Predeclared validation target reached')
    metadata['selection_uses_test']=False
    metadata['training_policy']=policy
    (model/'training_run.json').write_text(json.dumps(metadata,indent=2))
    print(json.dumps(metadata,indent=2),flush=True)

if __name__=='__main__':main()
