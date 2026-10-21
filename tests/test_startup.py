import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import app

class ModelStartupTests(unittest.TestCase):
    def test_token_libraries_initialize_before_the_first_http_request(self):
        events=[]
        with patch.dict(os.environ,{'TOKEN_MODEL_PATH':'startup-test','EXTRACTION_MODE':'auto'}), patch('backend.app.get_token_model',side_effect=lambda:events.append('model')), patch('backend.app.pytesseract.get_languages',side_effect=lambda **kwargs:events.append('health') or ['eng']):
            with TestClient(app) as client:
                self.assertEqual(events,['model'])
                self.assertEqual(client.get('/health').status_code,200)
                self.assertEqual(events,['model','health'])

if __name__=='__main__':unittest.main()
