"""Finalize a complete saved checkpoint after a predeclared validation target is met."""
import argparse
import json
import shutil
from pathlib import Path
from safetensors import safe_open
from transformers import AutoProcessor

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--checkpoint',required=True)
    parser.add_argument('--output',default='models/layoutlmv3-gpu-v2')
    parser.add_argument('--processor',default='models/layoutlmv3-indian-invoices')
    parser.add_argument('--target',type=float,default=.99)
    args=parser.parse_args()
    source,target=Path(args.checkpoint),Path(args.output)
    state=json.loads((source/'trainer_state.json').read_text())
    if state.get('best_metric',-1)<args.target:
        raise ValueError('Validation target not reached')
    with safe_open(str(source/'model.safetensors'),framework='pt',device='cpu') as weights:
        if not list(weights.keys()):
            raise ValueError('Checkpoint weights are empty')
    for name in ('config.json','model.safetensors','training_args.bin'):
        shutil.copyfile(source/name,target/name)
    AutoProcessor.from_pretrained(args.processor,apply_ocr=False).save_pretrained(target)
    path=target/'training_run.json'
    metadata=json.loads(path.read_text())
    metadata.update({'completed_optimizer_steps':state['global_step'],'completed_epochs':state['epoch'],
                     'selected_checkpoint':str(source),'target_validation_f1':args.target,
                     'stop_reason':'Predeclared synthetic validation target reached; finalized completed checkpoint',
                     'validation_at_selected_checkpoint':state['best_metric']})
    path.write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(json.dumps(metadata,indent=2),flush=True)

if __name__=='__main__':
    main()
