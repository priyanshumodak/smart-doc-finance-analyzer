import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image,ImageStat
from reportlab.pdfgen import canvas
from pathlib import Path
from reportlab.lib.utils import ImageReader
from fastapi.testclient import TestClient
from backend.app import app
from backend.candidates import rule_candidates,fuse,reconcile_candidates
from backend.layout_extractor import extract_fields
from backend.table_extraction import extract_items
from backend import storage


def digital_invoice(pages=1,identity='NATIVE-TEST-1'):
    buffer=io.BytesIO()
    doc=canvas.Canvas(buffer,pagesize=(595,842))
    for number in range(1,pages+1):
        doc.setFont('Helvetica',12)
        for index,text in enumerate(['Vendor: Native Seller Ltd','TAX INVOICE',f'Invoice No: {identity}','Invoice Date: 01/01/2020',f'Page {number} of {pages}']):
            doc.drawString(40,790-index*24,text)
        for x,text in [(40,'Description'),(300,'Qty'),(370,'Rate'),(470,'Amount')]:
            doc.drawString(x,620,text)
        for x,text in [(40,'Office Paper'),(300,str(number)),(370,'100.00'),(470,f'{number*100:.2f}')]:
            doc.drawString(x,590,text)
        if number==pages:
            subtotal=sum(range(1,pages+1))*100
            for y,text in [(530,f'Subtotal: {subtotal:.2f}'),(505,f'Total GST: {subtotal*.18:.2f}'),(480,f'Grand Total: {subtotal*1.18:.2f}')]:
                doc.drawString(320,y,text)
        doc.showPage()
    doc.save()
    return buffer.getvalue()

class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.environment=patch.dict(os.environ,{'DATABASE_PATH':self.directory.name+'/test.sqlite3','EXTRACTION_MODE':'ocr'})
        self.environment.start()
        self.client=TestClient(app)
        self.client.__enter__()
    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.environment.stop()
        self.directory.cleanup()
    def upload(self,raw=None):
        with patch('backend.app.run_ocr',side_effect=AssertionError('Native PDF must not call OCR')):
            response=self.client.post('/extract',files={'file':('native.pdf',raw or digital_invoice(),'application/pdf')})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()
    def test_native_pdf_skips_ocr_and_retains_aligned_preview(self):
        result=self.upload()
        page=result['pages'][0]
        self.assertEqual(page['text_source'],'pdf_text')
        self.assertEqual(page['fields']['invoice_number']['value'],'NATIVE-TEST-1')
        self.assertEqual(page['line_items'][0]['amount'],100)
        self.assertEqual(result['status'],'ok')
        response=self.client.get(f"/documents/{result['id']}/pages/1/preview")
        image=Image.open(io.BytesIO(response.content))
        self.assertEqual(list(image.size),page['image_size'])
        boxes=page['fields']['invoice_number']['boxes']
        self.assertTrue(boxes)
        crop=image.crop(boxes[0]).convert('L')
        self.assertLess(ImageStat.Stat(crop).extrema[0][0],200)
    def test_continuation_combines_rows_before_document_reconciliation(self):
        result=self.upload(digital_invoice(2))
        summary=result['document_summary']
        self.assertEqual(summary['document_count'],1)
        document=summary['documents'][0]
        self.assertEqual(document['pages'],[1,2])
        self.assertEqual(sum(item['amount'] for item in document['line_items']),300)
        self.assertEqual(document['status'],'ok')
    def test_separate_invoice_numbers_remain_separate(self):
        from backend.document_summary import summarize
        first=self.upload()['pages'][0]
        second=json.loads(json.dumps(first))
        second['page']=2
        second['fields']['invoice_number']['value']='ANOTHER-2'
        self.assertEqual(summarize([first,second])['document_count'],2)
    def test_mixed_pdf_uses_ocr_only_for_scanned_page(self):
        from backend.pdf_text import load_document
        buffer=io.BytesIO()
        document=canvas.Canvas(buffer,pagesize=(595,842))
        document.drawString(40,780,'Vendor Example invoice number one date January twenty subtotal tax total')
        document.showPage()
        image=Image.new('RGB',(595,842),'white')
        document.drawImage(ImageReader(image),0,0,width=595,height=842)
        document.save()
        packets=load_document(buffer.getvalue(),'mixed.pdf')
        self.assertEqual([packet['text_source'] for packet in packets],['pdf_text','ocr'])
        self.assertIsNone(packets[1]['tokens'])
    def test_competing_totals_are_retained_and_flagged(self):
        fields=extract_fields(Image.new('RGB',(20,20)),
                              'Seller: Test Ltd\nInvoice No: A\nInvoice Date: 01/01/2020\nSubtotal: 100\nTotal GST: 18\nGrand Total: 118\nGrand Total: 999')
        fields=reconcile_candidates(fields,[{'amount':100}])
        self.assertEqual(fields['total_amount']['value'],'118')
        self.assertTrue(fields['total_amount']['review_required'])
        self.assertEqual({item['value'] for item in fields['total_amount']['candidates']},{'118','999'})
    def test_common_invoice_label_variants(self):
        fields=extract_fields(Image.new('RGB',(20,20)),
                              'Supplier: Example Ltd\nInv No: X-1\nDate of Issue: 01/01/2020\nSubtotal: 100\nGST Total: 18\nInvoice Total: 118')
        self.assertEqual(fields['invoice_number']['value'],'X-1')
        self.assertEqual(fields['invoice_date']['value'],'01/01/2020')
        self.assertEqual(fields['tax_amount']['value'],'18')
        self.assertEqual(fields['total_amount']['value'],'118')

    def test_spaced_subtotal_and_due_date_do_not_compete_with_primary_fields(self):
        fields=extract_fields(Image.new('RGB',(20,20)),
                              'Due  Date: 15/01/2020\nInvoice Date: 01/01/2020\nSub Total: 100\nGST Total: 18\nGrand Total: 118')
        self.assertEqual(fields['invoice_date']['value'],'01/01/2020')
        self.assertEqual(fields['total_amount']['value'],'118')
        self.assertFalse(fields['total_amount']['review_required'])

    def test_low_model_candidates_do_not_hide_labelled_values(self):
        diagnostics={}
        with patch.dict(os.environ,{'EXTRACTION_MODE':'auto','TOKEN_MODEL_PATH':'test-model'}),patch('backend.layout_extractor.token_fields',return_value={'total_amount':{'value':'999','confidence':.1,'boxes':[]}}):
            fields=extract_fields(Image.new('RGB',(20,20)),'Grand Total: 118',diagnostics=diagnostics)
        self.assertEqual(fields['total_amount']['value'],'118')
        self.assertTrue(any(not item['eligible'] for item in fields['total_amount']['candidates']))
        self.assertEqual(diagnostics['token_model']['status'],'executed')
    def test_review_approval_export_alignment_and_invalidation(self):
        result=self.upload()
        document_id=result['id']
        endpoint=f'/documents/{document_id}/pages/1/approve-training'
        self.assertEqual(self.client.post(endpoint).status_code,409)
        corrected=self.client.patch('/documents/'+document_id,json={'page':1,'fields':{}})
        self.assertEqual(corrected.status_code,200)
        approved=self.client.post(endpoint)
        self.assertEqual(approved.status_code,200,approved.text)
        self.assertTrue(approved.json()['ready_for_training'])
        self.assertEqual(len(storage.training_reviews()),1)
        self.client.patch('/documents/'+document_id,json={'page':1,'fields':{'vendor_name':'Corrected absent text'}})
        self.assertEqual(storage.training_reviews(),[])
        pending=self.client.post(endpoint)
        self.assertEqual(pending.status_code,200,pending.text)
        self.assertFalse(pending.json()['ready_for_training'])
        self.assertIn('vendor_name',pending.json()['unmatched_fields'])
    def test_reserved_evaluation_invoice_cannot_be_approved(self):
        result=self.upload(digital_invoice(identity='INV-202600851'))
        document_id=result['id']
        self.client.patch('/documents/'+document_id,json={'page':1,'fields':{}})
        # This guard must work on a clone with no downloaded/generated dataset.
        fixture=Path(self.directory.name)/'reserved_data'/'fixture'
        fixture.mkdir(parents=True)
        (fixture/'manifest.json').write_text('{}')
        (fixture/'test.json').write_text(json.dumps([{'invoice_number':'INV-202600851'}]))
        with patch('backend.review_training.DATA_ROOT',fixture.parent):
            self.assertEqual(self.client.post(f'/documents/{document_id}/pages/1/approve-training').status_code,409)
    def test_transaction_correction_rechecks_balances(self):
        document_id='1'*32
        rows=[{'date':'01/01/2020','description':'Opening','balance':1000,'debit':None,'credit':None},
              {'date':'02/01/2020','description':'Shop','balance':800,'debit':200,'credit':None}]
        page={'page':1,'document_type':'bank_statement','fields':{},'line_items':[],'transactions':rows,
              'ocr_text':'BANK STATEMENT','ocr_tokens':[{'text':'Bank','box':[0,0,20,20],'norm_box':[0,0,200,200],'conf':95}],
              'validation':{'status':'ok','issues':[],'amount_reconciliation':{'status':'ok','checks':[]}}}
        storage.save({'id':document_id,'filename':'bank.png','created_at':'2020-01-01','status':'ok','num_pages':1,'pages':[page]})
        changed=json.loads(json.dumps(rows))
        changed[1]['balance']=900
        response=self.client.patch('/documents/'+document_id,json={'page':1,'transactions':changed})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['status'],'review_needed')
        restored=self.client.patch('/documents/'+document_id,json={'page':1,'transactions':rows})
        self.assertEqual(restored.json()['status'],'ok')
        changed[1]['debit']='not a number'
        self.assertEqual(self.client.patch('/documents/'+document_id,json={'page':1,'transactions':changed}).status_code,400)

    def test_row_discount_is_reconciled(self):
        from backend.validation import validate_amounts
        fields={name:{'value':value} for name,value in {'subtotal':180,'tax_amount':32.4,'total_amount':212.4}.items()}
        result=validate_amounts(fields,[{'qty':2,'rate':100,'discount':'10%','amount':180}])
        self.assertEqual(result['status'],'ok')

    def test_explicit_tax_inclusive_rows_reconcile_against_net_subtotal(self):
        from backend.validation import validate_amounts
        fields={name:{'value':value} for name,value in {'subtotal':180,'tax_amount':32.4,'total_amount':212.4}.items()}
        items=[{'qty':2,'rate':100,'discount':'10%','tax':'18%','amount':212.4}]
        report=validate_amounts(fields,items)
        self.assertEqual(report['status'],'ok')
        self.assertEqual(items[0]['amount_basis'],'tax_inclusive')

    def test_extended_columns_and_wrapped_description(self):
        rows=[[(10,'Description'),(350,'HSN'),(500,'Qty'),(600,'Rate'),(750,'Amount')],
              [(10,'Printer'),(350,'8443'),(500,'2'),(600,'100.00'),(750,'200.00')],
              [(10,'cartridge replacement pack')],[(10,'Subtotal:'),(750,'200.00')]]
        tokens=[{'text':text,'box':[x,y*30,x+max(20,len(text)*6),y*30+20]} for y,row in enumerate(rows) for x,text in row]
        items,_=extract_items(tokens)
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]['description'],'Printer cartridge replacement pack')
        self.assertEqual(items[0]['hsn'],'8443')
        self.assertEqual(items[0]['qty'],2)

if __name__=='__main__':
    unittest.main()
