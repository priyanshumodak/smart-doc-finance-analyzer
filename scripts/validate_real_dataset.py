"""Validate real receipt images, value labels, original splits and provenance."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from PIL import Image


def validate(root):
    root=Path(root)
    manifest=json.loads((root/'manifest.json').read_text())
    truth=json.loads((root/'ground_truth.json').read_text())
    rows=[json.loads(line) for line in (root/'annotations.jsonl').read_text().splitlines() if line]
    assert manifest['real_documents'] is True
    assert manifest['license']=='CC-BY-4.0'
    assert len(truth)==len(rows)==manifest['documents']
    indexed={record['id']:record for record in truth}
    ids,digests=set(),set(); counts=Counter(); labels=Counter()
    for row in rows:
        record=indexed[row['id']]
        assert row['id'] not in ids; ids.add(row['id'])
        assert record['split']==row['split']
        digest=hashlib.sha256((root/row['image_path']).read_bytes()).hexdigest()
        assert digest==row['sha256']==record['sha256']
        digests.add(digest)
        original=(root/'original_annotations'/f"{row['id']}.json").read_bytes()
        assert hashlib.sha256(original).hexdigest()==record['annotation_sha256']
        with Image.open(root/row['image_path']) as image: assert list(image.size)==row['image_size']
        assert len(row['words'])==len(row['boxes'])==len(row['labels'])>0
        for box in row['boxes']: assert len(box)==4 and 0<=box[0]<=box[2]<=1000 and 0<=box[1]<=box[3]<=1000
        assert set(record['annotated_fields'])<={'subtotal','tax_amount','total_amount'}
        assert not set(record.get('ambiguous_reference_fields',{}))&set(record['annotated_fields'])
        labels.update(row['labels']); counts[row['split']]+=1
    assert dict(counts)==manifest['splits']
    return {'status':'passed','source_duplicate_records':len(rows)-len(digests),'documents':len(rows),'splits':dict(counts),'labels':dict(labels),'unique_images':len(digests),'license':manifest['license']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--data',default='data/cord_real_v2'); parser.add_argument('--out',default='reports/real_receipts/validation.json'); args=parser.parse_args()
    result=validate(args.data); path=Path(args.out); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
