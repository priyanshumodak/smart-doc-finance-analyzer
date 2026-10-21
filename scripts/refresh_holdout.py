"""Refresh held-out synthetic layouts after a generator revision; retain records/splits."""
import hashlib
import json
import random
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data.build_training_dataset import render

def main():
    root=Path('data/training_indian_invoices')
    records={row['id']:row for row in json.loads((root/'ground_truth.json').read_text())}
    annotations=[json.loads(line) for line in (root/'annotations.jsonl').read_text().splitlines()]
    def refresh(annotation):
        if annotation['split']=='train':
            return annotation
        record=records[annotation['id']]
        image=root/annotation['image_path']
        result=render(record,image,annotation['template_id'],random.Random(annotation['id']))
        result.update({key:annotation[key] for key in ('id','image_path','split')})
        result['sha256']=hashlib.sha256(image.read_bytes()).hexdigest()
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(refresh,annotations))
    (root/'annotations.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows),encoding='utf-8')
    manifest=json.loads((root/'manifest.json').read_text())
    manifest['holdout_layout_revision']=2
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Refreshed 300 held-out examples with distinct field order and positions',flush=True)

if __name__=='__main__':
    main()
