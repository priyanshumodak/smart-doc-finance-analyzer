"""Validate training artifacts, checksums, split isolation and financial consistency."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from collections import Counter
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.validation import validate_gstin,validate_amounts

def validate(root):
    root=Path(root)
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8-sig'))
    records=json.loads((root/'ground_truth.json').read_text(encoding='utf-8-sig'))
    annotations=[json.loads(line) for line in (root/'annotations.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    assert len(records)==len(annotations)==manifest['documents']
    indexed={row['id']:row for row in records}
    ids,hashes=set(),set()
    counts,labels=Counter(),Counter()
    for row in annotations:
        assert row['id'] not in ids,'Duplicate ID'
        ids.add(row['id'])
        image_path=root/row['image_path']
        digest=hashlib.sha256(image_path.read_bytes()).hexdigest()
        assert digest==row['sha256'],'Image digest mismatch'
        assert digest not in hashes,'Duplicate image across dataset'
        hashes.add(digest)
        with Image.open(image_path) as image:
            assert list(image.size)==row['image_size']
        assert len(row['words'])==len(row['boxes'])==len(row['labels'])
        for box in row['boxes']:
            assert len(box)==4 and all(0<=v<=1000 for v in box) and box[0]<=box[2] and box[1]<=box[3]
        for relation in row['relations']:
            assert relation['key_word_ids'] and relation['value_word_ids']
            assert all(0<=index<len(row['words']) for index in relation['key_word_ids']+relation['value_word_ids'])
        record=indexed[row['id']]
        assert record['split']==row['split']
        assert validate_gstin(record['gstin']) and record['pan']==record['gstin'][2:12]
        fields={key:{'value':record[key]} for key in ('subtotal','tax_amount','total_amount','cgst','sgst','igst')}
        assert validate_amounts(fields,record['line_items'])['status']=='ok'
        expected_templates=range(6) if row['split']=='train' else ([6] if row['split']=='validation' else [7])
        assert row['template_id'] in expected_templates
        counts[row['split']]+=1
        labels.update(row['labels'])
    assert dict(counts)==manifest['splits']
    return {'documents':len(records),'splits':dict(counts),'unique_images':len(hashes),'labels':dict(labels),'status':'passed'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',default='data/training_indian_invoices')
    parser.add_argument('--output',default='reports/dataset_validation.json')
    args=parser.parse_args()
    report=validate(args.data)
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    main()
