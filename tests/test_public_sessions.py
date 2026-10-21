"""Public session access and legacy schema migration regressions."""
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import app
from backend import storage

class PublicSessionsTests(unittest.TestCase):
    def test_isolation_and_clear(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {'DATABASE_PATH':temporary+'/documents.sqlite3','PUBLIC_DEMO_MODE':'1'}):
            first={'X-Visitor-Session':'a'*64}
            second={'X-Visitor-Session':'b'*64}
            identity='c'*32
            token=storage.visitor.set('a'*64)
            try:
                storage.save({'id':identity,'filename':'private.pdf','created_at':'2026-01-01','status':'ok','pages':[]})
            finally:
                storage.visitor.reset(token)
            with TestClient(app) as client:
                self.assertEqual(client.get('/documents').status_code,401)
                self.assertEqual(client.get('/documents',headers=first).json()['documents'][0]['id'],identity)
                self.assertEqual(client.get('/documents',headers=second).json()['documents'],[])
                for suffix in ('','/excel','/pages/1/preview'):
                    self.assertEqual(client.get('/documents/'+identity+suffix,headers=second).status_code,404)
                self.assertEqual(client.patch('/documents/'+identity,headers=second,json={'page':1,'fields':{}}).status_code,404)
                self.assertEqual(client.get('/training-reviews',headers=first).status_code,403)
                self.assertEqual(client.post('/documents/'+identity+'/pages/1/approve-training',headers=first).status_code,403)
                self.assertEqual(client.delete('/documents',headers=second).json()['deleted'],0)
                self.assertEqual(client.get('/documents/'+identity,headers=first).status_code,200)
                self.assertEqual(client.delete('/documents',headers=first).json()['deleted'],1)
                self.assertEqual(client.get('/documents/'+identity,headers=first).status_code,404)

    def test_legacy_database_migration(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {'DATABASE_PATH':temporary+'/old.sqlite3'}):
            db=sqlite3.connect(os.environ['DATABASE_PATH'])
            db.execute('CREATE TABLE documents (id TEXT PRIMARY KEY, filename TEXT, created_at TEXT, status TEXT, result TEXT)')
            db.execute("INSERT INTO documents VALUES ('old','old.pdf','2026','ok','{}')")
            db.commit()
            db.close()
            self.assertEqual(storage.get('old'),{})

    def test_uploaded_document_keeps_request_owner_in_worker_thread(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {'DATABASE_PATH':temporary+'/documents.sqlite3','PUBLIC_DEMO_MODE':'1','EXTRACTION_MODE':'ocr'}):
            owner={'X-Visitor-Session':'d'*64}
            other={'X-Visitor-Session':'e'*64}
            sample=Path(__file__).resolve().parents[1]/'sample_docs/demo_digital_invoice.pdf'
            with TestClient(app) as client:
                response=client.post('/extract',headers=owner,files={'file':(sample.name,sample.read_bytes())})
                self.assertEqual(response.status_code,200,response.text)
                identity=response.json()['id']
                self.assertEqual(client.get('/documents/'+identity,headers=owner).status_code,200)
                self.assertEqual(client.get('/documents/'+identity,headers=other).status_code,404)
                self.assertEqual(len(client.get('/documents',headers=owner).json()['documents']),1)
                self.assertEqual(client.get('/documents',headers=other).json()['documents'],[])
