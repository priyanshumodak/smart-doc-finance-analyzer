"""Keep independent field candidates, validate formats and explain ranking decisions."""
import itertools
import re
try:
    from .validation import money,validate_gstin,validate_date
except ImportError:
    from validation import money,validate_gstin,validate_date

AMOUNTS={'subtotal','tax_amount','total_amount','cgst','sgst','igst','discount','round_off'}

def key(field,value):
    if value is None:
        return ''
    if field in AMOUNTS:
        number=money(value)
        return str(number.normalize()) if number is not None else str(value).casefold()
    if field in ('invoice_date','due_date'):
        parsed=validate_date(value,allow_future=True)
        if parsed['valid']:
            return parsed['value']
    return re.sub(r'\s+',' ',str(value)).strip().casefold()

def evidence(value,tokens):
    words=str(value or '').split()
    target=re.sub(r'[^\w]','',str(value).casefold())
    if not target:
        return []
    for start in range(len(tokens)):
        for count in range(max(1,len(words)-1),min(len(words)+3,len(tokens)-start+1)):
            subset=tokens[start:start+count]
            joined=re.sub(r'[^\w]','',' '.join(token['text'] for token in subset).casefold())
            if joined==target:
                return [token['box'] for token in subset]
    return []

def candidate(field,value,source,confidence,tokens,score=None):
    value=str(value).strip() if value is not None else None
    result={'value':value,'source':source,'confidence':confidence,'boxes':evidence(value,tokens),
            'selection_score':score if score is not None else float(confidence or 0),'eligible':bool(value),'reasons':[]}
    valid=True
    if field in AMOUNTS:
        valid=money(value) is not None
    elif field=='gstin':
        valid=validate_gstin(value)
    elif field=='pan':
        valid=bool(re.fullmatch(r'[A-Z]{5}\d{4}[A-Z]',(value or '').upper()))
    elif field=='ifsc':
        valid=bool(re.fullmatch(r'[A-Z]{4}0[A-Z0-9]{6}',(value or '').upper()))
    elif field in ('invoice_date','due_date'):
        valid=validate_date(value,allow_future=field=='due_date')['valid']
    result['format_valid']=valid
    if not valid:
        result['selection_score']-=.35
        result['reasons'].append('Format/checksum/date check failed; human review required')
    elif field in ('gstin','pan','ifsc','invoice_date','due_date'):
        result['selection_score']+=.08
    return result

def rule_candidates(text,tokens,labels,patterns):
    pools={field:[] for field in set(labels)|set(patterns)}
    try:
        from .layout_extractor import group_rows
    except ImportError:
        from layout_extractor import group_rows
    rows=group_rows(tokens)
    def located(item,position):
        row_index=text[:position].count('\n')
        for row in rows[row_index:row_index+2]:
            boxes=evidence(item['value'],row)
            if boxes:
                item['boxes']=boxes
                break
        return item
    for field,pattern in patterns.items():
        for match in pattern.finditer(text):
            score=.6
            prefix=text[max(0,match.start()-24):match.start()].split('\n')[-1].lower()
            if 'seller' in prefix or 'supplier' in prefix:
                score=.85
            pools[field].append(located(candidate(field,match.group().upper(),'regex_fallback',.5,tokens,score),match.start()))
    for field,label in labels.items():
        for match in re.finditer(label+r'\s*[:#-]?\s*([^\n]+)',text,re.I):
            prefix=text[:match.start()].split('\n')[-1]
            if field=='total_amount' and re.search(r'\b(?:sub|gst|tax)\s*$',prefix,re.I):
                continue
            if field=='invoice_date' and re.search(r'\bdue\s*$',prefix,re.I):
                continue
            value=re.split(r'\s{2,}|\s+(?:PAN|GSTIN|Due Date|Date)\s*:',match[1],maxsplit=1,flags=re.I)[0].strip()
            if field in AMOUNTS:
                number=re.match(r'(?:INR|Rs\.?|₹)?\s*(?:\([-+]?\d[\d,]*(?:\.\d+)?\)|[-+]?\d[\d,]*(?:\.\d+)?)',value,re.I)
                value=number.group().strip() if number else ''
            if value:
                pools.setdefault(field,[]).append(located(candidate(field,value,'label_fallback',.5,tokens,.78),match.start()))
    # Date headings, identifiers and table headings are never vendor names.
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    if lines and not re.search(r'invoice|receipt|statement|report|GSTIN|\bPAN\b|\bdate\b',lines[0],re.I):
        pools.setdefault('vendor_name',[]).append(candidate('vendor_name',lines[0],'first_line_heuristic',.3,tokens,.35))
    return pools

def choose(field,pool):
    eligible=[item for item in pool if item.get('eligible',True)]
    if not eligible:
        return {'value':None,'confidence':0.0,'source':'missing','boxes':[],'candidates':pool,'review_required':False}
    winner=max(eligible,key=lambda item:item['selection_score'])
    comparison_pool=[item for item in eligible if item.get('source')=='human_review'] if winner.get('source')=='human_review' else eligible
    alternatives={key(field,item['value']) for item in comparison_pool if item['selection_score']>=.6 and item.get('format_valid',True)}
    conflict=len(alternatives)>1
    return {**winner,'candidates':pool,'review_required':conflict or not winner.get('format_valid',True),
            'selection_reason':'Highest ranked eligible source with format checks; multiple credible values require review' if conflict else 'Highest ranked eligible source with format checks'}

def fuse(pools,fields):
    result={field:choose(field,pools.get(field,[])) for field in fields}
    gstin=result.get('gstin',{}).get('value')
    if gstin and validate_gstin(gstin):
        for item in pools.get('pan',[]):
            if (item.get('value') or '').upper()==gstin[2:12].upper():
                item['selection_score']+=.15
                item['reasons'].append('PAN agrees with selected GSTIN')
        if pools.get('pan'):
            result['pan']=choose('pan',pools['pan'])
    return result

def reconcile_candidates(fields,line_items):
    """Use arithmetic only to rank already observed credible values; never manufacture a field."""
    names=('subtotal','tax_amount','total_amount')
    choices=[]
    for name in names:
        pool=fields.get(name,{}).get('candidates',[])
        credible=sorted([item for item in pool if item.get('eligible') and item.get('format_valid') and money(item['value']) is not None],key=lambda x:x['selection_score'],reverse=True)[:3]
        if not credible:
            return fields
        choices.append(credible)
    discount=money(fields.get('discount',{}).get('value')) or 0
    rounding=money(fields.get('round_off',{}).get('value')) or 0
    amounts=[money(item.get('amount')) for item in line_items]
    line_sum=sum(amounts) if amounts and all(value is not None for value in amounts) else None
    ranked=[]
    for combination in itertools.product(*choices):
        subtotal,tax,total=[money(item['value']) for item in combination]
        support=abs(subtotal+tax-discount+rounding-total)<=1
        rows_agree=line_sum is not None and abs(line_sum-subtotal)<=1
        score=sum(item['selection_score'] for item in combination)+(.35 if support else 0)+(.25 if rows_agree else 0)
        ranked.append((score,support,rows_agree,combination))
    _,support,rows_agree,winners=max(ranked,key=lambda row:row[0])
    if support:
        for name,winner in zip(names,winners):
            previous=fields[name]
            fields[name]={**previous,**winner,'candidates':previous.get('candidates',[]),
                          'review_required':previous.get('review_required',False),
                          'selection_reason':'Observed candidates supported by subtotal/tax/total arithmetic'+(' and line-item sum' if rows_agree else '')}
    return fields
