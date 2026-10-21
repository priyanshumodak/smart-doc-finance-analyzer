"""Rendered dashboard regressions, including the OCR-ready sidebar branch."""
import unittest
from unittest.mock import patch,Mock
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP=Path(__file__).resolve().parents[1]/'streamlit_app.py'

def response(method,url,**kwargs):
    if url.endswith('/health'):
        value={'ocr_available':True,'extraction_mode':'ocr'}
    elif url.endswith('/documents'):
        value={'documents':[]}
    else:
        value={}
    result=Mock(ok=True)
    result.json.return_value=value
    return result

class DashboardTests(unittest.TestCase):
    def test_ocr_ready_and_empty_state_render(self):
        with patch('requests.request',side_effect=response):
            app=AppTest.from_file(str(APP),default_timeout=30).run()
        self.assertEqual(len(app.exception),0,[e.message for e in app.exception])
        self.assertTrue(any(element.value=='OCR ready' for element in app.success))
        self.assertTrue(any('Upload a document' in element.value for element in app.info))

    def test_saved_document_review_renders(self):
        result={'id':'test-document','filename':'test.png','num_pages':1,'status':'insufficient_data','processing_seconds':1,
                'pages':[{'page':1,'fields':{'vendor_name':{'value':'Test Seller','confidence':.5,'source':'label_fallback'}},
                          'line_items':[],'ocr_text':'Test Seller','image_size':[100,100],'ocr_tokens':[],
                          'validation':{'status':'insufficient_data','issues':[],
                                        'amount_reconciliation':{'checks':[{'rule':'subtotal + tax == total','passed':None}]}}}]}
        app=AppTest.from_file(str(APP),default_timeout=30)
        app.session_state['result']=result
        with patch('requests.request',side_effect=response):
            app.run()
        self.assertEqual(len(app.exception),0,[e.message for e in app.exception])
        self.assertTrue(any('Insufficient evidence' in element.value for element in app.info))

    def test_source_highlight_and_combined_summary_render(self):
        import io
        from PIL import Image
        buffer=io.BytesIO()
        Image.new('RGB',(100,100),'white').save(buffer,format='PNG')
        result={'id':'preview-test','filename':'native.pdf','num_pages':1,'status':'ok','processing_seconds':.2,
                'pages':[{'page':1,'document_type':'invoice','preview_available':True,'text_source':'pdf_text',
                          'fields':{'vendor_name':{'value':'Seller','confidence':.5,'source':'label_fallback','boxes':[[10,10,60,30]]}},
                          'line_items':[],'ocr_text':'Seller','image_size':[100,100],'ocr_tokens':[],
                          'validation':{'status':'ok','issues':[],'amount_reconciliation':{'checks':[{'rule':'sum','passed':True}]}}}],
                'document_summary':{'document_count':1,'grouping_policy':'matching invoice numbers','documents':[{
                    'document':1,'pages':[1],'status':'ok','fields':{},'line_items':[],'validation':{'issues':[]}}]}}
        def mock_request(method,url,**kwargs):
            if url.endswith('/preview'):
                return Mock(ok=True,content=buffer.getvalue())
            return response(method,url,**kwargs)
        app=AppTest.from_file(str(APP),default_timeout=30)
        app.session_state['result']=result
        with patch('requests.request',side_effect=mock_request):
            app.run()
            control=next(item for item in app.selectbox if item.label=='Highlight a field')
            control.set_value('vendor_name').run()
        self.assertEqual(len(app.exception),0,[e.message for e in app.exception])
        self.assertTrue(any('embedded PDF text' in element.value for element in app.caption))

    def test_bank_review_submit_contains_transactions(self):
        result={'id':'bank-test','filename':'bank.png','num_pages':1,'status':'ok','processing_seconds':1,
                'pages':[{'page':1,'document_type':'bank_statement','fields':{},'line_items':[],
                          'transactions':[{'date':'01/01/2020','description':'Opening','debit':None,'credit':None,'balance':1000}],
                          'ocr_text':'BANK STATEMENT','image_size':[100,100],'ocr_tokens':[],
                          'validation':{'status':'ok','issues':[],'amount_reconciliation':{'checks':[]}}}]}
        sent=[]
        def mock_request(method,url,**kwargs):
            if method=='PATCH':
                sent.append(kwargs['json'])
                out=Mock(ok=True)
                out.json.return_value=result
                return out
            return response(method,url,**kwargs)
        app=AppTest.from_file(str(APP),default_timeout=30)
        app.session_state['result']=result
        with patch('requests.request',side_effect=mock_request):
            app.run()
            next(button for button in app.button if button.label=='Save corrections and revalidate').click().run()
        self.assertEqual(len(app.exception),0,[e.message for e in app.exception])
        self.assertEqual(sent[0]['transactions'][0]['balance'],1000)

if __name__=='__main__':
    unittest.main()
