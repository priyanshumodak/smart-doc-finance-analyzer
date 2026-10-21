"""Run the existing extraction/review functions directly, with no HTTP server."""
import json
import re
from pathlib import Path
import requests
from fastapi import HTTPException
from pydantic import ValidationError
from . import app, storage


def request(method, path, **kwargs):
    identity = kwargs.get('headers',{}).get('X-Visitor-Session','')
    response = requests.Response()
    response.encoding = 'utf-8'
    token = storage.visitor.set(identity)
    try:
        if not re.fullmatch(r'[a-f0-9]{64}',identity):
            raise HTTPException(401,'A valid visitor session is required')
        method = method.upper()
        binary = None
        if 'approve-training' in path or path == '/training-reviews':
            raise HTTPException(403,'Training collection is disabled on the public demo')
        if method == 'GET' and path == '/health':
            value = app.health()
        elif method == 'POST' and path == '/extract':
            upload = kwargs.get('files',{}).get('file')
            if not upload or len(upload)<2 or not isinstance(upload[1],bytes):
                raise HTTPException(400,'Select a document to upload')
            raw,filename = app.validate_upload(upload[1],upload[0])
            value = app.process(raw,filename)
        elif method == 'GET' and path == '/documents':
            params = kwargs.get('params',{})
            value = app.documents(q=str(params.get('q','')),limit=50,offset=0)
        elif method == 'DELETE' and path == '/documents':
            value = app.clear_documents()
        else:
            match = re.fullmatch(r'/documents/([a-f0-9]{32})(?:/(excel|pages/[0-9]+/preview))?',path)
            if not match:
                raise HTTPException(404,'Not found')
            identity,suffix = match.groups()
            if method == 'GET' and suffix == 'excel':
                binary = app.document_excel(identity).body
            elif method == 'GET' and suffix and suffix.startswith('pages/'):
                preview = app.page_preview(identity,int(suffix.split('/')[1]))
                binary = Path(preview.path).read_bytes()
            elif method == 'GET' and suffix is None:
                value = app.document(identity)
            elif method == 'PATCH' and suffix is None:
                value = app.correct_document(identity,app.Correction(**kwargs.get('json',{})))
            else:
                raise HTTPException(405,'Method not allowed')
        response.status_code = 200
        response._content = binary if binary is not None else json.dumps(value,ensure_ascii=False).encode('utf-8')
    except HTTPException as exc:
        response.status_code = exc.status_code
        response._content = json.dumps({'detail':exc.detail}).encode()
    except (ValidationError,TypeError,ValueError):
        response.status_code = 400
        response._content = json.dumps({'detail':'Invalid request values'}).encode()
    finally:
        storage.visitor.reset(token)
    return response
