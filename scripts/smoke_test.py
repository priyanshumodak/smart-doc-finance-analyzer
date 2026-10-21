"""Real OCR smoke test on a generated invoice; no model downloads required."""
import io
import os
import tempfile
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['EXTRACTION_MODE']='ocr'
from fastapi.testclient import TestClient
from backend.app import app
from data.generate_synthetic_indian_invoices import build_invoice_record,render_invoice_image

with tempfile.TemporaryDirectory() as folder:
    os.environ['DATABASE_PATH']=folder+'/smoke.sqlite3'
    path=Path(folder)/'invoice.png'
    record=build_invoice_record(1)
    render_invoice_image(record,str(path))
    with TestClient(app) as client:
        health=client.get('/health').json()
        print('Health:',health)
        response=client.post('/extract',files={'file':(path.name,path.read_bytes(),'image/png')})
        response.raise_for_status()
        result=response.json()
        page=result['pages'][0]
        print('OCR text:',page['ocr_text'])
        print('OCR tokens:',page['ocr_token_count'])
        print('Extracted rows:',len(page['line_items']))
        print('Extracted invoice:',page['fields']['invoice_number']['value'])
        print('Status:',result['status'])
        assert page['ocr_token_count'] > 10,'OCR did not recover sufficient text'
        assert page['fields']['invoice_number']['value']==record['invoice_number'],'Invoice number was not extracted'
        workbook=client.get('/documents/'+result['id']+'/excel')
        assert workbook.status_code==200 and workbook.content.startswith(b'PK')
        print('Real OCR + persistence + Excel smoke test passed')
