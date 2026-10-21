"""Train a spatial key/value pair classifier; report relation F1 on held-out layouts."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_recall_fscore_support
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.relation_model import features,union

def examples(rows):
    inputs,targets=[],[]
    for row in rows:
        relations=row['relations']
        values=[union([row['boxes'][i] for i in relation['value_word_ids']]) for relation in relations]
        for index,relation in enumerate(relations):
            key=union([row['boxes'][i] for i in relation['key_word_ids']])
            for candidate,value in enumerate(values):
                inputs.append(features(key,value))
                targets.append(int(index==candidate))
    return np.asarray(inputs),np.asarray(targets)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',default='data/training_indian_invoices')
    parser.add_argument('--output',default='models/spatial-relations.json')
    args=parser.parse_args()
    rows=[json.loads(line) for line in (Path(args.data)/'annotations.jsonl').read_text().splitlines()]
    split={name:[row for row in rows if row['split']==name] for name in ('train','validation','test')}
    x,y=examples(split['train'])
    scaler=StandardScaler().fit(x)
    model=LogisticRegression(class_weight='balanced',random_state=42,max_iter=1000).fit(scaler.transform(x),y)
    output={'type':'spatial_logistic_regression','mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),
            'coefficients':model.coef_[0].tolist(),'intercept':float(model.intercept_[0]),
            'training_documents':len(split['train']),'training_pairs':len(y),
            'scope':'Candidate key/value pair classification from annotated spans. Synthetic layout benchmark; not FUNSD or end-to-end OCR relation accuracy.'}
    for name in ('validation','test'):
        tx,ty=examples(split[name])
        predictions=model.predict(scaler.transform(tx))
        precision,recall,f1,_=precision_recall_fscore_support(ty,predictions,average='binary',zero_division=0)
        output[name]={'documents':len(split[name]),'pairs':len(ty),'precision':float(precision),'recall':float(recall),'f1':float(f1)}
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps(output,indent=2),flush=True)

if __name__=='__main__':
    main()
