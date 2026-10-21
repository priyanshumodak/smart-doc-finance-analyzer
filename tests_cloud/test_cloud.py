"""Render the actual Community Cloud entrypoint with no network backend."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]

class CloudAppTests(unittest.TestCase):
    def test_samples_download_and_clear_without_backend(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{'DATABASE_PATH':directory+'/cloud.sqlite3'}), patch('requests.request',side_effect=AssertionError('External API must not be used')):
            app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=90).run()
            self.assertFalse(app.exception,[e.message for e in app.exception])
            self.assertTrue(any(e.value=='OCR ready' for e in app.success))
            next(b for b in app.button if b.label=='Analyze this sample').click().run(timeout=90)
            self.assertFalse(app.exception,[e.message for e in app.exception])
            self.assertEqual(app.session_state['result']['filename'],'demo_digital_invoice.pdf')
            self.assertEqual(app.session_state['result']['status'],'ok')
            self.assertFalse(any(b.label=='Approve page for training' for b in app.button))
            second=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=90).run()
            self.assertFalse(second.exception)
            history=next(s for s in second.selectbox if s.label=='Saved documents')
            self.assertEqual(len(history.options),1)
            next(b for b in app.button if b.label=='Prepare Excel download').click().run(timeout=90)
            self.assertFalse(app.exception,[e.message for e in app.exception])
            self.assertTrue(any(b.label=='Download Excel' for b in app.get('download_button')))
            next(b for b in app.button if b.label=='Clear my documents').click().run(timeout=90)
            self.assertFalse(app.exception,[e.message for e in app.exception])
            self.assertNotIn('result',app.session_state)

    def test_scanned_sample_runs_real_ocr_without_backend(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{'DATABASE_PATH':directory+'/scan.sqlite3'}), patch('requests.request',side_effect=AssertionError('External API must not be used')):
            app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=120).run()
            next(s for s in app.selectbox if s.label=='Fictional sample').select('Scanned invoice (OCR)').run()
            next(b for b in app.button if b.label=='Analyze this sample').click().run(timeout=120)
            self.assertFalse(app.exception,[e.message for e in app.exception])
            result=app.session_state['result']
            self.assertEqual(result['filename'],'demo_invoice.png')
            self.assertEqual(result['pages'][0]['text_source'],'ocr')
            self.assertGreater(result['pages'][0]['ocr_token_count'],0)
