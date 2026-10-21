"""Exercise generated document families with real OCR and record their checks."""
import json
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['EXTRACTION_MODE']='ocr'
os.environ.pop('TOKEN_MODEL_PATH',None)
from backend.app import process

def main():
    root=Path(__file__).resolve().parents[1]
    report=[]
    with tempfile.TemporaryDirectory() as folder:
        os.environ['DATABASE_PATH']=folder+'/demo.sqlite3'
        for filename in ('demo_invoice.pdf','demo_receipt.png','demo_bank_statement.png','demo_financial_report.pdf','demo_multipage.pdf'):
            path=root/'sample_docs'/filename
            result=process(path.read_bytes(),filename)
            summary={'filename':filename,'pages':result['num_pages'],'status':result['status'],
                     'details':[{'type':page['document_type'],'tokens':page['ocr_token_count'],
                                 'line_items':len(page['line_items']),'transactions':len(page.get('transactions',[])),
                                 'financial_metrics':len(page.get('financial_metrics',[])),
                                 'validation':page['validation']} for page in result['pages']]}
            report.append(summary)
            print(filename,result['num_pages'],result['status'],flush=True)
    (root/'reports/demo_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert report[-1]['pages']==2,'Multipage PDF did not retain all pages'
    statement=next(row for row in report if row['filename']=='demo_bank_statement.png')['details'][0]
    assert statement['type']=='bank_statement' and statement['transactions']>=2,'Statement table was not recovered'
    financial=next(row for row in report if row['filename']=='demo_financial_report.pdf')['details'][0]
    assert financial['type']=='financial_report' and financial['financial_metrics']>=3,'Report metrics were not recovered'
    print('All document-family smoke checks passed',flush=True)

if __name__=='__main__':
    main()
