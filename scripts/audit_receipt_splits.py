"""Protect evaluation using decoded image pixels, not filenames or PNG encoding."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from PIL import Image


def audit(root):
    root=Path(root)
    rows=json.loads((root/'ground_truth.json').read_text(encoding='utf-8'))
    groups=defaultdict(list);pixels={}
    for row in rows:
        with Image.open(root/row['image_path']) as original:
            image=original.convert('RGB')
            digest=hashlib.sha256(str(image.size).encode()+image.tobytes()).hexdigest()
        groups[digest].append({'id':row['id'],'split':row['split']});pixels[row['id']]=digest
    reserved={pixels[row['id']] for row in rows if row['split'] in ('validation','test')}
    safe=[];excluded=[];seen=set()
    for row in rows:
        if row['split']!='train': continue
        digest=pixels[row['id']]
        reason='matches validation/test pixels' if digest in reserved else 'duplicate training pixels' if digest in seen else None
        if reason: excluded.append({'id':row['id'],'reason':reason})
        else: safe.append(row['id']);seen.add(digest)
    return {'source_records_sha256':hashlib.sha256((root/'ground_truth.json').read_bytes()).hexdigest(),'documents':len(rows),'unique_pixel_images':len(groups),'duplicate_groups':[rows for rows in groups.values() if len(rows)>1],
            'safe_training_ids':safe,'safe_training_receipts':len(safe),'excluded_training_records':excluded,'pixel_hashes':pixels,
            'policy':'Never fit validation/test pixels; keep only one copy of each training image'}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--data',default='data/cord_real_full');parser.add_argument('--out',default='reports/indonesian/split_audit.json');args=parser.parse_args()
    report=audit(args.data);path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2))
    print(json.dumps({key:value for key,value in report.items() if key not in ('pixel_hashes','safe_training_ids')},indent=2),flush=True)
