"""Conservative page grouping with document-level field, row and balance reconciliation."""
import re
try:
    from .candidates import key,choose,reconcile_candidates
    from .document_validation import validate_document
    from .validation import money
except ImportError:
    from candidates import key,choose,reconcile_candidates
    from document_validation import validate_document
    from validation import money

CONTINUED=re.compile(r'\bcontinued\b|\bpage\s+[2-9]\d*\s*(?:of|/)\s*\d+',re.I)

def review_reasons(page):
    reasons=[]
    if not page.get('ocr_tokens'):
        reasons.append({'code':'unreadable_page','message':'No readable text was recovered'})
    confidence=[token['conf'] for token in page.get('ocr_tokens',[]) if token.get('conf') is not None]
    if confidence and sum(confidence)/len(confidence)<60:
        reasons.append({'code':'low_ocr_quality','message':'Average OCR confidence is below 60; inspect the source page'})
    for name,data in page.get('fields',{}).items():
        if data.get('review_required'):
            reasons.append({'code':'conflicting_or_invalid_field','field':name,'message':f'{name}: conflicting candidates or a failed format check'})
    for issue in page.get('validation',{}).get('issues',[]):
        reasons.append({'code':'validation_issue','message':issue})
    for check in page.get('validation',{}).get('amount_reconciliation',{}).get('checks',[]):
        if check.get('passed') is False:
            reasons.append({'code':'arithmetic_mismatch','message':check['rule'],'expected':check.get('expected'),'actual':check.get('actual')})
    return reasons

def summarize(pages):
    groups=[]
    for page in pages:
        invoice=key('invoice_number',page.get('fields',{}).get('invoice_number',{}).get('value'))
        current=groups[-1] if groups else None
        continuation=bool(CONTINUED.search(page.get('ocr_text','')))
        merge=current is not None and ((invoice and invoice==current['invoice_number']) or (not invoice and continuation))
        if not merge:
            current={'invoice_number':invoice,'pages':[]}
            groups.append(current)
        current['pages'].append(page)
    documents=[]
    for index,group in enumerate(groups,1):
        members=group['pages']
        fields={}
        names={name for page in members for name in page.get('fields',{})}
        for name in names:
            pool=[]
            for page in members:
                data=page['fields'].get(name,{})
                if data.get('applicable') is False:
                    continue
                candidates=data.get('candidates') or ([data] if data.get('value') is not None else [])
                for candidate in candidates:
                    item={**candidate,'page':page['page'],'eligible':candidate.get('eligible',True),
                          'selection_score':candidate.get('selection_score',float(candidate.get('confidence') or 0))}
                    if item.get('source')=='human_review':
                        item['selection_score']=10
                    pool.append(item)
            fields[name]=choose(name,pool)
        items=[{**item,'page':page['page'],'row_index':row+1} for page in members for row,item in enumerate(page.get('line_items',[]))]
        transactions=[{**item,'page':page['page']} for page in members for item in page.get('transactions',[])]
        balance_checks=[]
        for previous,current in zip(transactions,transactions[1:]):
            before,after=money(previous.get('balance')),money(current.get('balance'))
            debit,credit=money(current.get('debit')),money(current.get('credit'))
            if before is None or after is None or (debit is None and credit is None):
                continue
            expected=before-(debit or 0)+(credit or 0)
            balance_checks.append({'rule':'previous balance - debit + credit == balance','expected':float(expected),
                                   'actual':float(after),'passed':abs(expected-after)<=money('0.01')})
        metrics=[{**item,'page':page['page']} for page in members for item in page.get('financial_metrics',[])]
        kind=next((page['document_type'] for page in members if page.get('document_type')!='unknown'),'unknown')
        if kind!='indonesian_receipt':
            fields=reconcile_candidates(fields,items)
        validation=validate_document(kind,fields,items,transactions,balance_checks,metrics)
        quality=[reason for page in members if not page.get('reviewed_at') for reason in page.get('review_reasons',[]) if reason.get('code') in ('low_ocr_quality','unreadable_page')]
        if quality:
            validation['status']='review_needed'
            validation['issues'].extend(reason['message'] for reason in quality)
        conflicts=[name for name,data in fields.items() if data.get('review_required')]
        if conflicts:
            validation['status']='review_needed'
            validation['issues'].append('Conflicting or invalid fields: '+', '.join(sorted(conflicts)))
        documents.append({'document':index,'pages':[page['page'] for page in members],'document_type':kind,
                          'fields':fields,'line_items':items,'transactions':transactions,'financial_metrics':metrics,
                          'balance_checks':balance_checks,'validation':validation,'status':validation['status']})
    statuses=[document['status'] for document in documents]
    status='review_needed' if 'review_needed' in statuses else ('ok' if statuses and all(value=='ok' for value in statuses) else 'insufficient_data')
    return {'documents':documents,'document_count':len(documents),'status':status,
            'grouping_policy':'Consecutive matching invoice numbers or explicit continuation markers; unrelated invoices remain separate'}
