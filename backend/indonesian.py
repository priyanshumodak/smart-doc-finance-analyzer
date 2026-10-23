"""Evidence-backed Indonesian receipt amounts; preserve text and item names."""
import re
from decimal import Decimal,InvalidOperation
try:
    from .layout_extractor import group_rows
except ImportError:
    from layout_extractor import group_rows

LABELS={
 'subtotal':(r'\b(?:sub[ -]?total|jumlah\s+belanja)\b','Subtotal'),
 'tax_amount':(r'\b(?:pajak|ppn|pb[1il]|tax|vat)\b','Tax'),
 'service_charge':(r'\b(?:service|svc\s*chrg|layanan)\b','Service charge'),
 'total_amount':(r'\b(?:grand\s*total|total\s*(?:bayar|belanja)|jumlah\s*bayar|amount\s*due|due|total)\b','Total'),
 'amount_paid':(r'\b(?:cash(?!\s*change)|tunai|bayar|paid|debit|kredit)\b','Amount paid'),
 'change':(r'\b(?:cash\s*change|change|kembali(?:an)?)\b','Change'),
 'discount':(r'\b(?:diskon|discount|disc)\b','Discount'),
 'round_off':(r'\b(?:rounding|round\s*off|pembulatan)\b','Rounding')}
ALIASES={'vendor_name':'Nama penjual','invoice_number':'Nomor struk','invoice_date':'Tanggal',
         'subtotal':'Subtotal','tax_amount':'Pajak','total_amount':'Total','service_charge':'Biaya layanan',
         'amount_paid':'Pembayaran','change':'Kembalian','discount':'Diskon','round_off':'Pembulatan'}
AMOUNT=re.compile(r'(?<![A-Za-z0-9])(?:Rp\.?\s*)?[-+]?\d[\d.,]*(?![A-Za-z0-9])',re.I)


def number(value):
    text=re.sub(r'(?i)(?:rp\.?|idr|\s)','',str(value or '')).strip().rstrip('.,')
    if not re.fullmatch(r'[+-]?\d+(?:[.,]\d+)*',text): return None
    pieces=re.split(r'[.,]',text)
    if len(pieces)>1:
        text=''.join(pieces) if len(pieces[-1])==3 else ''.join(pieces[:-1])+'.'+pieces[-1]
    try: return Decimal(text)
    except InvalidOperation: return None


def detect(text):
    return bool(re.search(r'(?i)\b(?:rupiah|pajak|tunai|kembalian|terima\s+kasih|pb[1il]|ppn|svc\s*chrg)\b|\bRp\.?\s*\d|\b(?:sub[ -]?total|total)\s*[:=]?\s*\d{1,3}(?:\.\d{3})+',text))


def fields(tokens, base):
    # Imported invoice candidates are not valid evidence for this locale.
    result={name:{'value':None,'confidence':0.0,'source':'missing','boxes':[],'candidates':[],'review_required':False} for name in base}
    for name in ('gstin','pan','cgst','sgst','igst','place_of_supply','due_date','bill_to','ifsc'):
        if name in result: result[name]['applicable']=False
    pools={}
    rows=group_rows(tokens)
    # Perspective can place the amount slightly above or below its printed label.
    # Pair only a nearby, numeric-only row to the right; do not guess from value size.
    used=set(); aligned=[]
    for row in rows:
        text=' '.join(t['text'] for t in row)
        numeric_only=number(text) is not None
        label=next((name for name,(pattern,_) in LABELS.items() if re.search(pattern,text,re.I)),None)
        if label and not numeric_only and not re.search(r'(?i)included|inclusive',text):
            existing=[m for m in AMOUNT.finditer(text) if not text[m.end():].lstrip().startswith('%')]
            if not existing:
                center=sum(t.get('row_y',(t['box'][1]+t['box'][3])/2) for t in row)/len(row)
                height=max(t['box'][3]-t['box'][1] for t in row)
                right=max(t['box'][2] for t in row)
                choices=[]
                for index,candidate_row in enumerate(rows):
                    if index in used or candidate_row is row: continue
                    candidate_text=' '.join(t['text'] for t in candidate_row)
                    if number(candidate_text) is None or min(t['box'][0] for t in candidate_row)<=right: continue
                    candidate_y=sum(t.get('row_y',(t['box'][1]+t['box'][3])/2) for t in candidate_row)/len(candidate_row)
                    distance=abs(candidate_y-center)
                    if distance<=max(12,height*1.8): choices.append((distance,index,candidate_row))
                if choices:
                    _,index,value_row=min(choices,key=lambda choice:choice[0]); used.add(index)
                    row=sorted(row+value_row,key=lambda token:token['box'][0])
        aligned.append(row)
    for row in aligned:
        text=' '.join(t['text'] for t in row)
        # OCR often inserts spaces immediately around thousands separators.
        numeric_text=re.sub(r'(?<=\d)\s+(?=[.,])','',text)
        numeric_text=re.sub(r'(?<=[.,])\s+(?=\d)','',numeric_text)
        matches=list(AMOUNT.finditer(numeric_text))
        text=numeric_text
        for name,(pattern,english) in LABELS.items():
            match=re.search(pattern,text,re.I)
            if not match: continue
            if name=='total_amount' and re.search(r'(?i)\b(?:sub[ -]?total|total\s+(?:tax|pajak|qty|item|items|quantity))\b',text): continue
            if name=='amount_paid' and re.search(r'(?i)change|kembali|total\s*bayar|jumlah\s*bayar',text): continue
            amounts=[m for m in matches if m.start()>=match.end() and not text[m.end():].lstrip().startswith('%')]
            if not amounts: continue
            observed=amounts[-1].group(); amount=number(observed)
            if amount is None: continue
            # The row is a single observed candidate, including its source boxes.
            score=.85+(0.08 if name=='total_amount' and re.search(r'(?i)grand|due|total\s*bayar',text) else 0)
            item={'value':format(amount,'f'),'normalized_value':format(amount,'f'),'currency':'IDR','source_text':observed,
                  'label_original':match.group(),'label_en':english,'source':'indonesian_receipt_label',
                  'confidence':None,'selection_score':score,'eligible':True,'format_valid':True,'reasons':[],
                  'boxes':[t['box'] for t in row if any(c.isdigit() for c in t['text'])],
                  'review_required':False,'raw_row':text}
            pools.setdefault(name,[]).append(item)
    # Learned fallback considers source rows only; no reference answers are available.
    try:
        from .receipt_classifier import predict
    except ImportError:
        from receipt_classifier import predict
    page_height=max((t['box'][3] for t in tokens),default=1)
    for row in group_rows(tokens):
        text=' '.join(t['text'] for t in row)
        y=sum(t.get('row_y',(t['box'][1]+t['box'][3])/2) for t in row)/len(row)/page_height
        predicted,model_score=predict(text,y)
        if predicted not in LABELS or predicted in pools or model_score<.95: continue
        if not re.search('[A-Za-z]{2}',text): continue
        matches=[m for m in AMOUNT.finditer(text) if not text[m.end():].lstrip().startswith('%')]
        if not matches: continue
        observed=matches[-1].group(); amount=number(observed)
        if amount is None: continue
        # Small quantities or percentages must not become totals from positional priors.
        if predicted in ('total_amount','subtotal','amount_paid') and abs(amount)<100: continue
        item={'value':format(amount,'f'),'normalized_value':format(amount,'f'),'source_text':observed,'currency':'IDR',
              'label_original':text[:matches[-1].start()].strip(),'label_en':LABELS[predicted][1],
              'source':'trained_indonesian_receipt_line','model_score':model_score,'confidence':None,
              'selection_score':.75,'eligible':True,'format_valid':True,'reasons':['Learned from official training receipts; inspect source'],
              'boxes':[t['box'] for t in row],'review_required':True,'raw_row':text}
        pools.setdefault(predicted,[]).append(item)
    for name,pool in pools.items():
        winner=max(pool,key=lambda item:item['selection_score'])
        result[name]={**winner,'candidates':pool,'review_required':winner.get('review_required',False) or len({r['value'] for r in pool})>1}
    source_text='\n'.join(' '.join(t['text'] for t in row) for row in group_rows(tokens))
    optional={'invoice_date':r'(?i)\b(?:tanggal|date)\s*[:=]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
              'invoice_number':r'(?i)\b(?:nota|struk|receipt|bill)\s*(?:no\.?|#|:)\s*([A-Z0-9][A-Z0-9/-]{2,})'}
    for name,pattern in optional.items():
        match=re.search(pattern,source_text)
        if match:
            result[name]={'value':match.group(1),'source':'indonesian_explicit_label','confidence':None,'source_text':match.group(1),
                          'boxes':[],'candidates':[],'review_required':False}
    return result


def validate(fields,items):
    get=lambda name:number(fields.get(name,{}).get('value')) if fields.get(name,{}).get('value') is not None else None
    checks=[]; issues=[]
    subtotal,tax,total=get('subtotal'),get('tax_amount'),get('total_amount')
    if subtotal is not None and total is not None:
        # Missing tax/service/discount are not invented as extracted values.
        extras=[get(n) for n in ('tax_amount','service_charge','discount','round_off')]
        expected=subtotal+(extras[0] or 0)+(extras[1] or 0)-(extras[2] or 0)+(extras[3] or 0)
        checks.append({'rule':'subtotal + observed tax + observed service - observed discount + observed rounding == total',
                       'expected':float(expected),'actual':float(total),'passed':abs(expected-total)<=1})
    paid,change=get('amount_paid'),get('change')
    if paid is not None and change is not None and total is not None:
        # CORD photos sometimes print change with a minus sign.
        expected=paid-abs(change)
        checks.append({'rule':'amount paid - absolute change == total','expected':float(expected),'actual':float(total),'passed':abs(expected-total)<=1})
    if total is None: issues.append('Total belum terbaca / Total was not read')
    if not checks: issues.append('Bukti belum cukup untuk rekonsiliasi / Insufficient observed amounts for reconciliation')
    status='review_needed' if total is None or any(c['passed'] is False for c in checks) else ('ok' if checks else 'insufficient_data')
    return {'document_schema':'indonesian_receipt','status':status,'amount_reconciliation':{'status':status,'checks':checks},
            'issues':issues,'gstin_valid':None,'date_check':None,'due_date_check':None}


def line_items(tokens):
    try:
        from .receipt_classifier import predict
    except ImportError:
        from receipt_classifier import predict
    result=[];page_height=max((t['box'][3] for t in tokens),default=1)
    for row in group_rows(tokens):
        text=' '.join(t['text'] for t in row)
        if any(re.search(pattern,text,re.I) for pattern,_ in LABELS.values()): continue
        match=re.match(r'^\s*(\d+(?:[.,]\d+)?)(?:\s*[xX]\s*|\s+)(.+?)\s+((?:Rp\.?\s*)?\d[\d.,]*)\s*$',text)
        quantity=None;model_score=None
        if match:
            qty,description,raw=match.groups();quantity=number(qty)
        else:
            match=re.match(r'^\s*(.+?)\s+((?:Rp\.?\s*)?\d[\d.,]*)\s*$',text)
            if not match: continue
            description,raw=match.groups()
            y=sum(t.get('row_y',(t['box'][1]+t['box'][3])/2) for t in row)/len(row)/page_height
            predicted,model_score=predict(text,y)
            if predicted!='menu' or model_score<.8: continue
        amount=number(raw)
        if amount is None or not re.search(r'[A-Za-z]{2}',description): continue
        rate=None
        tail=re.search(r'\s+(\d[\d.,]*)$',description)
        if tail and quantity is not None:
            observed=number(tail[1])
            if observed is not None and abs(observed*quantity-amount)<=1:
                rate=float(observed);description=description[:tail.start()].strip()
        result.append({'description':description.strip(),'qty':float(quantity) if quantity is not None else None,'rate':rate,'amount':float(amount),
                       'source':'indonesian_receipt_row','source_amount':raw,'currency':'IDR','model_score':model_score,
                       'review_required':quantity is None,'raw_row':text,
                       'box':[min(t['box'][0] for t in row),min(t['box'][1] for t in row),max(t['box'][2] for t in row),max(t['box'][3] for t in row)]})
    return result
