"""Import a publisher-licensed external Indian invoice corpus without inventing token labels."""
import argparse
import hashlib
import json
import random
from pathlib import Path
from datasets import load_dataset
from itertools import islice

DATASET='build-small-hackathon/kirana-invoice-train-data'
MAPPING={'supplier':'vendor_name','gstin_supplier':'gstin','buyer':'bill_to','invoice_number':'invoice_number',
         'date':'invoice_date','subtotal':'subtotal','gst_total':'tax_amount','invoice_total':'total_amount','grand_total':'total_amount'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='data/kirana_external')
    parser.add_argument('--limit',type=int,default=0,help='Per publisher split; zero imports all 500 examples')
    args=parser.parse_args()
    root=Path(args.out)
    if (root/'manifest.json').exists():
        parser.error('Output already exists; choose another folder')
    (root/'images').mkdir(parents=True,exist_ok=True)
    records=[]
    for source_split in ('train','test'):
        stream=load_dataset(DATASET,split=source_split,streaming=True)
        stream=islice(stream,args.limit) if args.limit else stream
        for index,example in enumerate(stream):
            annotation=json.loads(example['response'])
            identity=f'kirana_{source_split}_{index:05d}'
            relative=f'images/{identity}.png'
            example['image'].convert('RGB').save(root/relative)
            record={'id':identity,'image_path':relative,'source_dataset':DATASET,'source_split':source_split,'split':source_split,
                    'sha256':hashlib.sha256((root/relative).read_bytes()).hexdigest(),'annotation_source':'publisher financial JSON; no manually verified token/BIO labels','currency':'INR'}
            record.update({destination:annotation[source] for source,destination in MAPPING.items() if source in annotation and annotation[source] is not None})
            record['publisher_annotation']=annotation
            source_items=annotation.get('line_items',annotation.get('items',[]))
            record['line_items']=[{'item':item.get('raw_name',item.get('product_raw','')),'qty':item.get('quantity'),'rate':item.get('unit_price'),
                                   'amount':item.get('total',item.get('line_total')),'gst_rate':item.get('gst_rate')} for item in source_items]
            record['annotated_fields']=sorted({field for field in MAPPING.values() if field in record})+(['line_items'] if 'line_items' in annotation or 'items' in annotation else [])
            records.append(record)
            if (index+1)%50==0:
                print(f'{source_split}: {index+1} imported',flush=True)
    train=[row for row in records if row['source_split']=='train']
    indices=list(range(len(train)))
    random.Random(42).shuffle(indices)
    validation=set(indices[:max(1,len(train)//10)])
    for index,row in enumerate(train):
        if index in validation:
            row['split']='validation'
    counts={split:sum(row['split']==split for row in records) for split in ('train','validation','test')}
    for name,rows in [('ground_truth',records)]+[(split,[row for row in records if row['split']==split]) for split in counts]:
        (root/f'{name}.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
    manifest={'name':'External Kirana Indian FMCG invoices','source_dataset':DATASET,
              'source_url':'https://huggingface.co/datasets/'+DATASET,'license':'CC0-1.0 (publisher card)',
              'documents':len(records),'splits':counts,'field_mapping':MAPPING,
              'validation_policy':'Seed 42 10% holdout from publisher training split; publisher test preserved',
              'data_type':'fully synthetic external layouts: printed GST, Tally-style, simulated handwriting and WhatsApp-style',
              'limitations':['Not real customer invoices','No token boxes/BIO labels supplied by publisher',
                             'Publisher financial JSON is retained without silently correcting it','Use annotated_fields masks for partial-schema evaluation']}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)

if __name__=='__main__':
    main()
