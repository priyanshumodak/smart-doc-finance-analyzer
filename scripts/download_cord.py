"""Import licensed real CORD-v2 receipts, retaining official splits and raw annotations."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import requests
from PIL import Image

SOURCE='naver-clova-ix/cord-v2'
MAPPING={'total.total_price':'total_amount','sub_total.subtotal_price':'subtotal','sub_total.tax_price':'tax_amount'}


def adapt(raw, identity, relative, split, size):
    width,height=size
    record={'id':identity,'image_path':relative,'split':split,'currency':'IDR','source':SOURCE,
            'annotated_fields':list(MAPPING.values())}
    for category,field in MAPPING.items():
        section,name=category.split('.')
        value=raw.get('gt_parse',{}).get(section,{}).get(name)
        if isinstance(value,(str,int,float)):
            record[field]=str(value)
    words,boxes,labels=[],[],[]
    for line in raw.get('valid_line',[]):
        field=MAPPING.get(line.get('category'))
        active=False
        for word in line.get('words',[]):
            words.append(word['text'])
            quad=word['quad']; xs=[quad[f'x{i}'] for i in range(1,5)]; ys=[quad[f'y{i}'] for i in range(1,5)]
            boxes.append([max(0,min(1000,round(min(xs)*1000/width))),max(0,min(1000,round(min(ys)*1000/height))),
                          max(0,min(1000,round(max(xs)*1000/width))),max(0,min(1000,round(max(ys)*1000/height)))])
            is_value=field is not None and word.get('is_key')==0
            labels.append(('I-' if active else 'B-')+field.upper() if is_value else 'O')
            active=is_value
    annotation={'id':identity,'image_path':relative,'split':split,'words':words,'boxes':boxes,'labels':labels,'relations':[],
                'image_size':[width,height],'annotation_source':'CORD-v2 official value-word labels; key words remain O'}
    return record,annotation


def viewer_rows(split,limit):
    response=requests.get('https://datasets-server.huggingface.co/first-rows',
        params={'dataset':SOURCE,'config':'default','split':split},timeout=60)
    response.raise_for_status()
    rows=response.json()['rows']
    if limit<=0 or limit>len(rows):
        raise ValueError(f'Viewer offers {len(rows)} cached {split} rows; choose a smaller --limit or --transport streaming for the full release')
    for entry in rows[:limit]:
        if entry.get('truncated_cells'):
            raise ValueError('Dataset viewer truncated annotations; use streaming rather than importing incomplete labels')
        row=entry['row']
        image_response=requests.get(row['image']['src'],timeout=60)
        image_response.raise_for_status()
        payload=image_response.content
        with Image.open(io.BytesIO(payload)) as image:
            size=image.size
        if size!=(row['image']['width'],row['image']['height']):
            raise ValueError('Viewer image dimensions differ from supplied annotation geometry')
        yield entry['row_idx'],payload,json.loads(row['ground_truth']),size


def streaming_rows(split,limit,revision):
    from datasets import load_dataset
    from itertools import islice
    dataset=load_dataset(SOURCE,split=split,streaming=True,revision=revision)
    for index,example in enumerate(islice(dataset,limit) if limit else dataset):
        image=example['image'].convert('RGB'); buffer=io.BytesIO(); image.save(buffer,format='PNG')
        yield index,buffer.getvalue(),json.loads(example['ground_truth']),image.size


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='data/cord_real_v2')
    parser.add_argument('--limit',type=int,default=20,help='Per original split. Zero requires streaming and imports the full release.')
    parser.add_argument('--transport',choices=['viewer','streaming'],default='viewer')
    args=parser.parse_args()
    if args.limit<0: parser.error('--limit must be nonnegative')
    root=Path(args.out)
    if root.exists(): parser.error('Output already exists; choose a new folder to preserve the existing data')
    metadata=requests.get('https://huggingface.co/api/datasets/'+SOURCE,timeout=30); metadata.raise_for_status()
    revision=metadata.json()['sha']
    (root/'images').mkdir(parents=True)
    (root/'original_annotations').mkdir()
    records,annotations,counts=[],[],{}
    for split in ('train','validation','test'):
        counts[split]=0
        rows=viewer_rows(split,args.limit) if args.transport=='viewer' else streaming_rows(split,args.limit,revision)
        for index,payload,raw,size in rows:
            identity=f'cord_{split}_{index:05d}'
            extension='.jpg' if payload.startswith(b'\xff\xd8') else '.png'
            relative=f'images/{identity}{extension}'
            (root/relative).write_bytes(payload)
            original=json.dumps(raw,ensure_ascii=False,indent=2).encode('utf-8')
            (root/'original_annotations'/f'{identity}.json').write_bytes(original)
            record,annotation=adapt(raw,identity,relative,split,size)
            digest=hashlib.sha256(payload).hexdigest()
            record.update({'sha256':digest,'source_index':index,'annotation_sha256':hashlib.sha256(original).hexdigest()})
            annotation['sha256']=digest
            records.append(record); annotations.append(annotation); counts[split]+=1
        print(f'{split}: {counts[split]} real receipts imported',flush=True)
    (root/'ground_truth.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    (root/'annotations.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in annotations),encoding='utf-8')
    for split in counts:
        (root/f'{split}.json').write_text(json.dumps([r for r in records if r['split']==split],ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={'name':'CORD-v2 real receipts mapped subset','source':'https://github.com/clovaai/cord','huggingface':SOURCE,
        'source_revision':revision,'transport':args.transport,'license':'CC-BY-4.0','real_documents':True,'splits':counts,
        'documents':len(records),'field_mapping':MAPPING,'adaptation':'Three monetary fields mapped; other labels O. Viewer images are publisher JPEG derivatives with checked dimensions.',
        'limitations':['Indonesian receipts with IDR amounts, not Indian GST invoices','Only total, subtotal and tax evaluated',
        'Original first-N split order retained; this subset is not representative of every layout','No relation or line-item benchmark in this adapter']}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    license_response=requests.get('https://raw.githubusercontent.com/clovaai/cord/master/LICENSE-CC-BY',timeout=30)
    license_response.raise_for_status(); (root/'LICENSE-CC-BY.txt').write_text(license_response.text,encoding='utf-8')
    (root/'ATTRIBUTION.md').write_text('CORD by Park et al., Clova AI/NAVER. https://github.com/clovaai/cord . CC-BY-4.0: https://creativecommons.org/licenses/by/4.0/ . Images and annotations downloaded from naver-clova-ix/cord-v2. See manifest.json for mappings, derivatives and scope.\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)

if __name__=='__main__': main()
