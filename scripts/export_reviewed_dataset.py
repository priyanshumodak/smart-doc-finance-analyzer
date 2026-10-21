"""Export only approved, aligned examples; preserve pending reviews and block evaluation leakage."""
import argparse
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import storage

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='data/reviewed_training')
    args=parser.parse_args()
    root=Path(args.out)
    if root.exists():
        parser.error('Choose a new output folder to preserve prior exports')
    rows=storage.training_reviews()
    ready=[row for row in rows if row['ready_for_training'] and not row.get('reserved_evaluation_document')]
    pending=[row for row in rows if row not in ready]
    (root/'images').mkdir(parents=True)
    annotations=[]
    truth=[]
    for row in ready:
        record={**row,'image_path':f"images/{row['id']}.png"}
        shutil.copyfile(storage.preview_path(row['document_id'],row['page']),root/record['image_path'])
        annotations.append(record)
        truth.append({'id':record['id'],'image_path':record['image_path'],'split':'train',**record['fields']})
    (root/'annotations.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in annotations),encoding='utf-8')
    (root/'ground_truth.json').write_text(json.dumps(truth,indent=2,ensure_ascii=False),encoding='utf-8')
    (root/'pending_alignment.json').write_text(json.dumps(pending,indent=2,ensure_ascii=False),encoding='utf-8')
    manifest={'documents':len(annotations),'splits':{'train':len(annotations)},'pending_alignment':len(pending),
              'annotation_source':'Human-approved fields matched to source OCR/PDF tokens','source':'local reviewed documents',
              'limitations':['Train-only supplement; use independent validation/test splits',
                             'Corrected values absent from OCR require manual token annotation and are not silently labelled']}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)

if __name__=='__main__':
    main()
