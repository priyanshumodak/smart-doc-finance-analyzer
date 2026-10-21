"""Refresh publisher annotations without redownloading existing images."""
import hashlib,json,time
from pathlib import Path
import requests
from download_kirana import DATASET,MAPPING
root=Path('data/kirana_external')
records=json.loads((root/'ground_truth.json').read_text())
by_source={(r['source_split'],int(r['id'].rsplit('_',1)[1])):r for r in records}
for split,count in [('train',450),('test',50)]:
    for offset in range(0,count,100):
        cache=root/'publisher_pages'/f'{split}_{offset}.json'
        cache.parent.mkdir(exist_ok=True)
        if cache.exists():
            payload=json.loads(cache.read_text())
        else:
            for attempt in range(5):
                response=requests.get('https://datasets-server.huggingface.co/rows',params={'dataset':DATASET,'config':'default','split':split,'offset':offset,'length':min(100,count-offset)},timeout=120)
                if response.ok:
                    break
                if attempt==4:
                    response.raise_for_status()
                time.sleep(2*(attempt+1))
            payload=response.json()
            cache.write_text(json.dumps(payload))
        for entry in payload['rows']:
            record=by_source[(split,entry['row_idx'])]
            annotation=json.loads(entry['row']['response'])
            record['publisher_annotation']=annotation
            record['sha256']=hashlib.sha256((root/record['image_path']).read_bytes()).hexdigest()
            record.update({dest:annotation[src] for src,dest in MAPPING.items() if annotation.get(src) is not None})
            items=annotation.get('line_items',annotation.get('items',[]))
            record['line_items']=[{'item':i.get('raw_name',i.get('product_raw','')),'qty':i.get('quantity'),'rate':i.get('unit_price'),'amount':i.get('total',i.get('line_total')),'gst_rate':i.get('gst_rate')} for i in items]
            record['annotated_fields']=sorted({v for v in MAPPING.values() if v in record})+(['line_items'] if 'line_items' in annotation or 'items' in annotation else [])
        print(split,offset,flush=True)
for name,rows in [('ground_truth',records)]+[(s,[r for r in records if r['split']==s]) for s in ('train','validation','test')]:
    (root/f'{name}.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
manifest=json.loads((root/'manifest.json').read_text());manifest['field_mapping']=MAPPING
manifest['limitations'].append('Visual spot-check: printed row amounts/rates may be rounded relative to publisher JSON; audit before exact row evaluation')
(root/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('Refreshed',len(records),'annotations',flush=True)
