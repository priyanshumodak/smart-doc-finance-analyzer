"""Approved field reviews become token annotations only when their source text is aligned."""
import hashlib
import json
import re
from datetime import datetime,timezone
from pathlib import Path
try:
    from .candidates import key
except ImportError:
    from candidates import key

DATA_ROOT=Path(__file__).resolve().parents[1]/'data'

FIELDS=['vendor_name','bill_to','invoice_number','invoice_date','due_date','gstin','pan','place_of_supply',
        'subtotal','tax_amount','total_amount','cgst','sgst','igst']

def build_review(result,page):
    tokens=page.get('ocr_tokens',[])
    words=[token['text'] for token in tokens]
    labels=['O']*len(words)
    unmatched=[]
    for field in FIELDS:
        data=page['fields'].get(field,{})
        value=data.get('value')
        if value is None or str(value).strip()=='':
            continue
        target=key(field,value)
        found=False
        # Prefer the selected field's evidence to disambiguate repeated amounts.
        preferred=set(tuple(box) for box in data.get('boxes',[]))
        starts=sorted(range(len(words)),key=lambda i:0 if tuple(tokens[i]['box']) in preferred else 1)
        for start in starts:
            for count in range(1,min(len(str(value).split())+5,len(words)-start+1)):
                if any(label!='O' for label in labels[start:start+count]):
                    continue
                if key(field,' '.join(words[start:start+count]))==target:
                    labels[start]='B-'+field.upper()
                    for offset in range(1,count):
                        labels[start+offset]='I-'+field.upper()
                    found=True
                    break
            if found:
                break
        if not found:
            unmatched.append(field)
    invoice=str(page['fields'].get('invoice_number',{}).get('value') or '')
    reserved=False
    reserved_sources=[]
    project_data=DATA_ROOT
    for manifest in project_data.glob('*/manifest.json'):
        data_root=manifest.parent
        for split in ('validation','test'):
            path=data_root/f'{split}.json'
            if not path.exists():
                continue
            records=json.loads(path.read_text(encoding='utf-8-sig'))
            for record in records:
                same_invoice=bool(invoice and str(record.get('invoice_number',''))==invoice)
                same_image=bool(result.get('source_sha256') and record.get('sha256')==result['source_sha256'])
                if same_invoice or same_image:
                    reserved=True
                    reserved_sources.append(f'{data_root.name}/{split}')
                    break
    return {'id':f"review_{result['id']}_{page['page']}",'document_id':result['id'],'page':page['page'],
            'approved_at':datetime.now(timezone.utc).isoformat(),'reviewed_at':page.get('reviewed_at'),
            'source_filename':result['filename'],'source_sha256':result.get('source_sha256'),
            'split':'train','words':words,'boxes':[token['norm_box'] for token in tokens],'labels':labels,
            'fields':{name:page['fields'].get(name,{}).get('value') for name in FIELDS},
            'unmatched_fields':unmatched,'reserved_evaluation_document':bool(reserved),'reserved_sources':sorted(set(reserved_sources)),
            'ready_for_training':not unmatched and not reserved,
            'annotation_source':'human-approved fields aligned to source words; not manually corrected OCR tokens'}
