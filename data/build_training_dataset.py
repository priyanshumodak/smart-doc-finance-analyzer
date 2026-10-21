"""Generate reproducible financial scans with exact word/BIO/box annotations and held-out layouts."""
import argparse
import hashlib
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data.generate_synthetic_indian_invoices import build_invoice_record

FIELDS=['vendor_name','bill_to','invoice_number','invoice_date','due_date','gstin','pan','place_of_supply',
        'subtotal','tax_amount','total_amount','cgst','sgst','igst']

def font(size,bold=False,serif=False):
    names = (['C:/Windows/Fonts/timesbd.ttf' if bold else 'C:/Windows/Fonts/times.ttf'] if serif else [])
    names += ['C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
              'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf']
    for name in names:
        try:
            return ImageFont.truetype(name,size)
        except OSError:
            pass
    raise RuntimeError('Install DejaVu Sans fonts or supply Arial on Windows')

def render(record,path,template,rng):
    width,height=1000,1400
    image=Image.new('RGB',(width,height),'white')
    draw=ImageDraw.Draw(image)
    regular=font(20,serif=template in (2,5,7))
    bold=font(24,bold=True,serif=template in (2,5,7))
    small=font(18,serif=template in (2,5,7))
    words,boxes,labels,relations=[],[],[],[]
    margin=35+(template%3)*12
    accent=['#17324d','#174c44','#5b334d'][template%3]
    draw.rectangle((0,0,width,75),fill=accent)
    def text(x,y,value,field=None,use_font=None,fill='black'):
        chosen=use_font or regular
        indices=[]
        for index,word in enumerate(str(value).split()):
            bounds=draw.textbbox((x,y),word,font=chosen)
            if bounds[2]>=width-10 or bounds[3]>=height:
                raise ValueError('Rendered text exceeds page bounds')
            draw.text((x,y),word,font=chosen,fill=fill)
            words.append(word)
            boxes.append([max(0,min(1000,round(bounds[0]*1000/width))),max(0,min(1000,round(bounds[1]*1000/height))),
                          max(0,min(1000,round(bounds[2]*1000/width))),max(0,min(1000,round(bounds[3]*1000/height)))])
            labels.append(('B-' if index==0 else 'I-')+field.upper() if field else 'O')
            indices.append(len(words)-1)
            x+=draw.textlength(word+' ',font=chosen)
        return indices
    text(margin,21,record['vendor_name'],'vendor_name',bold,'white')
    text(margin,90,'TAX INVOICE',use_font=bold)
    if template%2:
        pairs=[('Invoice Number','invoice_number'),('Invoice Date','invoice_date'),('Due Date','due_date'),
               ('Seller GSTIN','gstin'),('Seller PAN','pan'),('Bill To','bill_to'),('Place of Supply','place_of_supply')]
    else:
        pairs=[('GSTIN','gstin'),('PAN','pan'),('Place of Supply','place_of_supply'),('Invoice No','invoice_number'),
               ('Date','invoice_date'),('Due Date','due_date'),('Bill To','bill_to')]
    if template==6:
        pairs=list(reversed(pairs))
    elif template==7:
        pairs=pairs[3:]+pairs[:3]
    for row,(key,field) in enumerate(pairs):
        y=145+row*(39+(template%2)*3)
        key_ids=text(margin,y,key+':')
        value_ids=text((400 if template>=6 else 300+(template%3)*20),y,record[field],field)
        relations.append({'field':field,'key_word_ids':key_ids,'value_word_ids':value_ids})
    table_y=500+(template%3)*22
    positions=[margin,580,685,825]
    for x,name in zip(positions,['Item','Qty','Rate','Amount']):
        text(x,table_y,name,use_font=bold)
    draw.line((margin,table_y+32,965,table_y+32),fill=accent,width=2)
    for row,item in enumerate(record['line_items']):
        y=table_y+45+row*39
        text(positions[0],y,item['item'],use_font=small)
        text(positions[1],y,item['qty'],use_font=small)
        text(positions[2],y,f"{item['rate']:.2f}",use_font=small)
        text(positions[3],y,f"{item['amount']:.2f}",use_font=small)
    summary_y=table_y+45+len(record['line_items'])*39+30
    summary=[('Subtotal','subtotal'),('CGST','cgst'),('SGST','sgst'),('IGST','igst'),
             ('Total GST','tax_amount'),('Grand Total','total_amount')]
    for row,(key,field) in enumerate(summary):
        y=summary_y+row*36
        keys=text(520,y,key+':',use_font=regular)
        values=text(800,y,f"{record[field]:.2f}",field,use_font=regular)
        relations.append({'field':field,'key_word_ids':keys,'value_word_ids':values})
    text(margin,1330,'SYNTHETIC TRAINING DOCUMENT - NOT A REAL TAX INVOICE',use_font=small,fill='gray')
    degradation='clean'
    if rng.random()<.35:
        image=ImageEnhance.Contrast(image).enhance(rng.uniform(.7,.95))
        image=image.filter(ImageFilter.GaussianBlur(rng.uniform(.15,.45)))
        degradation='mild_blur_contrast'
    image.save(path)
    return {'words':words,'boxes':boxes,'labels':labels,'relations':relations,'image_size':[width,height],
            'template_id':template,'degradation':degradation,'annotation_source':'renderer_exact'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--n',type=int,default=1000)
    parser.add_argument('--out',default='data/training_indian_invoices')
    parser.add_argument('--seed',type=int,default=42)
    args=parser.parse_args()
    if args.n<20:
        parser.error('Use at least 20 examples for separate train/validation/test sets')
    root=Path(args.out)
    if (root/'manifest.json').exists():
        parser.error('Dataset already exists; choose a new output folder to preserve split provenance')
    (root/'images').mkdir(parents=True,exist_ok=True)
    random.seed(args.seed)
    rng=random.Random(args.seed)
    records,annotations=[],[]
    train_count=int(args.n*.7)
    val_count=int(args.n*.15)
    counts=Counter()
    for index in range(args.n):
        split='train' if index<train_count else ('validation' if index<train_count+val_count else 'test')
        template=rng.randrange(6) if split=='train' else (6 if split=='validation' else 7)
        record=build_invoice_record(index+1)
        tax=round(record['tax_amount'],2)
        interstate=rng.random()<.4
        record.update({'cgst':0 if interstate else round(tax/2,2),
                       'sgst':0 if interstate else round(tax-round(tax/2,2),2),
                       'igst':tax if interstate else 0})
        relative=f'images/invoice_{index+1:05d}.png'
        record.update({'id':f'invoice_{index+1:05d}','image_path':relative,'split':split,'template_id':template})
        annotation=render(record,root/relative,template,rng)
        annotation.update({'id':record['id'],'image_path':relative,'split':split,
                           'sha256':hashlib.sha256((root/relative).read_bytes()).hexdigest()})
        records.append(record)
        annotations.append(annotation)
        counts[split]+=1
        if (index+1)%100==0:
            print(f'Generated {index+1}/{args.n}',flush=True)
    (root/'ground_truth.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    (root/'annotations.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in annotations),encoding='utf-8')
    for split in counts:
        (root/f'{split}.json').write_text(json.dumps([r for r in records if r['split']==split],indent=2),encoding='utf-8')
    manifest={'name':'Synthetic Indian Financial Invoices','version':'2.0','seed':args.seed,'documents':args.n,
              'splits':dict(counts),'fields':FIELDS,'labels':['O']+[f'{prefix}-{name.upper()}' for name in FIELDS for prefix in ('B','I')],
              'split_strategy':'70/15/15 with train layouts 0-5, validation layout 6, test layout 7',
              'annotation_source':'exact renderer word boxes and BIO labels, not OCR predictions',
              'limitations':['Synthetic English printed invoices only','Not a real-world accuracy benchmark',
                             'Validation/test use held-out templates but related fonts and vocabulary'],
              'generator':'data/build_training_dataset.py'}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)

if __name__=='__main__':
    main()
