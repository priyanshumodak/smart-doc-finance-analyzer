"""Measure native-text and forced-OCR paths on identical generated digital PDFs."""
import json
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['EXTRACTION_MODE']='ocr'
os.environ.pop('TOKEN_MODEL_PATH',None)
from backend.app import process
ROOT=Path(__file__).resolve().parents[1]

def main():
    rows=[]
    with tempfile.TemporaryDirectory() as folder:
        os.environ['DATABASE_PATH']=folder+'/benchmark.sqlite3'
        for name in ('demo_digital_invoice.pdf','demo_continued_invoice.pdf'):
            path=ROOT/'sample_docs'/name
            for mode in ('auto','ocr'):
                os.environ['TEXT_EXTRACTION_MODE']=mode
                result=process(path.read_bytes(),name)
                summary=result['document_summary']
                row={'file':name,'text_mode':mode,'seconds':result['processing_seconds'],
                     'page_sources':[page['text_source'] for page in result['pages']],
                     'documents':summary['document_count'],'status':result['status'],
                     'line_items':sum(len(document['line_items']) for document in summary['documents']),
                     'total':summary['documents'][0]['fields']['total_amount']['value']}
                rows.append(row)
                print(json.dumps(row),flush=True)
    output=ROOT/'reports/pdf_path_comparison.json'
    output.write_text(json.dumps({'scope':'Functional and timing comparison on two generated digital PDF cases; not a real-document accuracy benchmark','runs':rows},indent=2),encoding='utf-8')
    native=[row for row in rows if row['text_mode']=='auto']
    assert all(all(source=='pdf_text' for source in row['page_sources']) for row in native)
    assert all(row['status']=='ok' for row in native)
    assert native[1]['line_items']==2 and native[1]['documents']==1
    print('Native PDF and continued-invoice checks passed',flush=True)

if __name__=='__main__':
    main()
