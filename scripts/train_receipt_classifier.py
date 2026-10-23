"""Train a compact line model only on the official CORD training split."""
import argparse
import hashlib
import json
import math
import sys
from collections import Counter,defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.receipt_classifier import features

CATEGORIES={'sub_total.subtotal_price':'subtotal','sub_total.tax_price':'tax_amount','total.total_price':'total_amount',
            'sub_total.service_price':'service_charge','total.cashprice':'amount_paid','total.changeprice':'change',
            'sub_total.discount_price':'discount','sub_total.etc':'round_off','menu.price':'menu'}


def train(root,out,audit_file=None):
    root=Path(root); files=sorted((root/'original_annotations').glob('cord_train_*.json'))
    if not files: raise ValueError('No official training annotations found')
    from scripts.audit_receipt_splits import audit
    split_audit=json.loads(Path(audit_file).read_text()) if audit_file else audit(root)
    if audit_file:
        if split_audit.get('source_records_sha256')!=hashlib.sha256((root/'ground_truth.json').read_bytes()).hexdigest():
            raise ValueError('Split audit belongs to different dataset records')
        records=json.loads((root/'ground_truth.json').read_text(encoding='utf-8'))
        for record in records:
            if hashlib.sha256((root/record['image_path']).read_bytes()).hexdigest()!=record['sha256']:
                raise ValueError('Image changed after the split audit')
    allowed=set(split_audit['safe_training_ids'])
    official_count=len(files)
    files=[path for path in files if path.stem in allowed]
    counts=defaultdict(Counter); documents=Counter(); frequency=Counter(); hashes=[]
    for path in files:
        raw=json.loads(path.read_text(encoding='utf-8'))
        lines=raw.get('valid_line',[])
        max_y=max((max(w['quad'].get('y3',0),w['quad'].get('y4',0)) for line in lines for w in line.get('words',[])),default=1)
        hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
        for line in lines:
            words=line.get('words',[])
            if not words: continue
            text=' '.join(w['text'] for w in words)
            y=sum((w['quad']['y1']+w['quad']['y3'])/2 for w in words)/len(words)/max_y
            category=line.get('category','')
            label='menu' if category.startswith('menu.') else CATEGORIES.get(category,'other')
            vector=features(text,y)
            counts[label].update(vector); documents[label]+=1; frequency.update(vector.keys())
    vocabulary={word for word,count in frequency.items() if count>=2}
    labels=sorted(counts); weights={}; priors={}
    for label in labels:
        total=sum(count for feature,count in counts[label].items() if feature in vocabulary)+len(vocabulary)
        weights[label]={feature:round(math.log((counts[label][feature]+1)/total),7) for feature in sorted(vocabulary)}
        priors[label]=-math.log(len(labels))
    model={'architecture':'multinomial_naive_bayes_receipt_line','labels':labels,'vocabulary':sorted(vocabulary),'weights':weights,'priors':priors,
           'metadata':{'source':'naver-clova-ix/cord-v2','license':'CC-BY-4.0','training_split':'train','receipts':len(files),
           'official_training_receipts':official_count,'excluded_training_records':split_audit['excluded_training_records'],'training_lines':sum(documents.values()),'line_classes':dict(documents),'training_annotation_sha256':hashlib.sha256(''.join(hashes).encode()).hexdigest(),
           'validation_or_test_used_for_fitting':False,'score_note':'Softmax score is not calibrated field correctness'}}
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(model,separators=(',',':')),encoding='utf-8')
    print(json.dumps(model['metadata'],indent=2),flush=True)
    print('Model bytes:',out.stat().st_size,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--data',default='data/cord_real_full');parser.add_argument('--out',default='backend/assets/indonesian_line_model.json');parser.add_argument('--split_audit');args=parser.parse_args();train(args.data,args.out,args.split_audit)
