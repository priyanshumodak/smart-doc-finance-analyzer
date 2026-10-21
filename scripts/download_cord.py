"""Import official CORD-v2 receipts using streaming; preserve original train/validation/test splits."""
import argparse
import hashlib
import json
from pathlib import Path
from itertools import islice
from datasets import load_dataset

MAPPING={'total.total_price':'total_amount','sub_total.subtotal_price':'subtotal','sub_total.tax_price':'tax_amount'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='data/cord_v2')
    parser.add_argument('--limit',type=int,default=20,help='Per split. Set 0 for all 1000 released receipts.')
    args=parser.parse_args()
    root=Path(args.out)
    if (root/'manifest.json').exists():
        parser.error('Output already exists; choose another folder')
    (root/'images').mkdir(parents=True,exist_ok=True)
    records,annotations,counts=[],[],{}
    for split in ('train','validation','test'):
        dataset=load_dataset('naver-clova-ix/cord-v2',split=split,streaming=True)
        examples=islice(dataset,args.limit) if args.limit else dataset
        counts[split]=0
        for index,example in enumerate(examples):
            identity=f'cord_{split}_{index:05d}'
            relative=f'images/{identity}.png'
            image=example['image'].convert('RGB')
            image.save(root/relative)
            raw=json.loads(example['ground_truth'])
            words,boxes,labels=[],[],[]
            width,height=image.size
            record={'id':identity,'image_path':relative,'split':split,'currency':'IDR','source':'naver-clova-ix/cord-v2'}
            for line in raw.get('valid_line',[]):
                category=MAPPING.get(line.get('category'))
                text=[]
                for word_index,word in enumerate(line.get('words',[])):
                    text.append(word['text'])
                    words.append(word['text'])
                    quad=word['quad']
                    xs=[quad[f'x{i}'] for i in range(1,5)]
                    ys=[quad[f'y{i}'] for i in range(1,5)]
                    boxes.append([max(0,min(1000,round(min(xs)*1000/width))),max(0,min(1000,round(min(ys)*1000/height))),
                                  max(0,min(1000,round(max(xs)*1000/width))),max(0,min(1000,round(max(ys)*1000/height)))])
                    labels.append(('B-' if word_index==0 else 'I-')+category.upper() if category else 'O')
                if category and text:
                    record[category]=' '.join(text)
            records.append(record)
            annotations.append({'id':identity,'image_path':relative,'split':split,'words':words,'boxes':boxes,'labels':labels,
                                'relations':[],'annotation_source':'CORD-v2 official valid_line annotations, mapped three finance fields',
                                'image_size':[width,height],'sha256':hashlib.sha256((root/relative).read_bytes()).hexdigest()})
            counts[split]+=1
        print(f'{split}: {counts[split]} imported',flush=True)
    (root/'ground_truth.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    (root/'annotations.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in annotations),encoding='utf-8')
    for split in counts:
        (root/f'{split}.json').write_text(json.dumps([row for row in records if row['split']==split],indent=2),encoding='utf-8')
    manifest={'name':'CORD-v2 mapped subset','source':'https://github.com/clovaai/cord','huggingface':'naver-clova-ix/cord-v2',
              'license':'CC-BY-4.0','splits':counts,'documents':len(records),'field_mapping':MAPPING,
              'limitations':['Indonesian receipts, not Indian GST invoices','Only total/subtotal/tax mapped; other categories labelled O',
                             'No relation benchmark labels in this adapter','Review long examples before token training']}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)

if __name__=='__main__':
    main()
