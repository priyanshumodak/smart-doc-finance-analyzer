"""Choose operating mode using identical validation examples, without changing extraction rules."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    scores={}
    for mode in ('ocr','token'):
        path=ROOT/'reports/validation_modes'/mode/'evaluation.json'
        record=json.loads(path.read_text(encoding='utf-8-sig'))
        if record.get('split')!='validation':raise ValueError('Mode selection must use validation data')
        scores[mode]=record
    baseline=scores['ocr']
    for record in scores.values():
        if any(record.get(key)!=baseline.get(key) for key in ('dataset','documents','offset','limit')):
            raise ValueError('Validation documents differ across modes')
    selected=max(scores,key=lambda mode:(scores[mode]['micro']['f1'],scores[mode]['micro']['precision'],mode=='ocr'))
    result={'recommended_mode':selected,'selection_metric':'Final-field F1 on identical validation examples',
        'validation_documents':baseline['documents'],'offset':baseline['offset'],'test_used_for_selection':False,
        'scores':{mode:r['micro'] for mode,r in scores.items()},
        'scope':'20 synthetic validation documents; no rules/weights changed. Diagnostic test comparison motivated checking operating modes; a separate reserved test slice is reported afterward.'}
    (ROOT/'run/preferred_mode.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (ROOT/'reports/validation_modes/selection.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
