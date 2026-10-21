"""Spreadsheet exports include fields, line items, checks and provenance."""
import io
import json
import pandas as pd

def safe(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    if isinstance(value, (list,dict)):
        return json.dumps(value,ensure_ascii=False)
    return value

def excel_bytes(result):
    fields, items, checks, evidence = [], [], [], []
    transactions, metrics, relations = [], [], []
    for page in result['pages']:
        number = page['page']
        transactions.extend({'page':number, **row} for row in page.get('transactions',[]))
        metrics.extend({'page':number, **row} for row in page.get('financial_metrics',[]))
        relations.extend({'page':number, **row} for row in page.get('relations',[]))
        checks.extend({'page':number, **row} for row in page.get('balance_checks',[]))
        row = {'page': number, 'status': page['validation']['status']}
        for name, data in page['fields'].items():
            row[name] = data.get('value')
            evidence.append({'page': number, 'field': name, **data})
        fields.append(row)
        items.extend({'page':number, **item} for item in page['line_items'])
        checks.extend({'page':number, **check} for check in page['validation']['amount_reconciliation']['checks'])
        checks.extend({'page':number, 'rule':issue, 'passed':False} for issue in page['validation'].get('issues',[]))
    summaries=[]
    merged=[]
    for document in result.get('document_summary',{}).get('documents',[]):
        row={'document':document['document'],'pages':document['pages'],'type':document['document_type'],'status':document['status']}
        row.update({name:data.get('value') for name,data in document['fields'].items()})
        summaries.append(row)
        merged.extend({'document':document['document'],**item} for item in document['line_items'])
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for name, rows in [('Fields', fields),('Line Items',items),('Validation',checks),('Provenance',evidence),('Transactions',transactions),('Financial Metrics',metrics),('Spatial Relations',relations),('Document Summary',summaries),('Merged Line Items',merged)]:
            pd.DataFrame([{k:safe(v) for k,v in row.items()} for row in rows]).to_excel(writer,sheet_name=name,index=False)
    return buffer.getvalue()
