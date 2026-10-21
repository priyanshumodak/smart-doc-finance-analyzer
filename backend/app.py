"""Bounded document ingestion, persistent review and reusable exports."""
import os
import time
import uuid
import logging
import hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Semaphore
from typing import Any
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response,FileResponse,JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
import pytesseract
try:
    from .preprocessing import load_pages, preprocess_page
    from .ocr_engine import run_ocr, tokens_to_dicts
    from .layout_extractor import extract_fields, extract_line_items, tokens_to_text, FIELD_QUESTIONS, get_token_model
    from .validation import run_validation
    from .document_validation import validate_document
    from .exports import excel_bytes
    from . import storage
    from .pdf_text import load_document
    from .table_extraction import extract_items,pdf_table_items
    from .candidates import reconcile_candidates,evidence
    from .document_summary import summarize,review_reasons,CONTINUED
    from .review_training import build_review
    from .document_tables import spatial_relations, statement_transactions, report_metrics
except ImportError:
    from preprocessing import load_pages, preprocess_page
    from ocr_engine import run_ocr, tokens_to_dicts
    from layout_extractor import extract_fields, extract_line_items, tokens_to_text, FIELD_QUESTIONS, get_token_model
    from validation import run_validation
    from document_validation import validate_document
    from exports import excel_bytes
    import storage
    from pdf_text import load_document
    from table_extraction import extract_items,pdf_table_items
    from candidates import reconcile_candidates,evidence
    from document_summary import summarize,review_reasons,CONTINUED
    from review_training import build_review
    from document_tables import spatial_relations, statement_transactions, report_metrics

@asynccontextmanager
async def lifespan(application):
    # Complete the legacy owner-column migration before concurrent requests.
    with storage.connect():
        pass
    # Initialize native CUDA libraries on the server's main startup thread.
    # Upload processing later runs in Starlette's worker pool.
    if os.getenv('TOKEN_MODEL_PATH') and os.getenv('EXTRACTION_MODE','auto')!='ocr':
        try:
            get_token_model()
        except Exception:
            logging.exception('Token model startup failed; extraction will retain OCR fallback')
    yield

app = FastAPI(title='Smart Document and Finance Analyzer',version='2.1.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS','http://localhost:8501').split(','),
                   allow_methods=['GET','POST','PATCH'],allow_headers=['Content-Type'])
@app.middleware('http')
async def visitor_scope(request, call_next):
    public = os.getenv('PUBLIC_DEMO_MODE','0') == '1'
    identity = 'local'
    if public and request.url.path != '/health':
        import re
        identity = request.headers.get('X-Visitor-Session','')
        if not re.fullmatch(r'[a-f0-9]{64}', identity):
            return JSONResponse({'detail':'A valid visitor session is required'}, status_code=401)
        if 'approve-training' in request.url.path or request.url.path == '/training-reviews':
            return JSONResponse({'detail':'Training collection is disabled on the public demo'}, status_code=403)
    token = storage.visitor.set(identity)
    try:
        return await call_next(request)
    finally:
        storage.visitor.reset(token)

@app.delete('/documents')
def clear_documents():
    return {'deleted':storage.clear_visitor()}

MAX_BYTES = int(os.getenv('MAX_UPLOAD_MB','20')) * 1024 * 1024
pipeline_lock = Semaphore(1)

@app.get('/health')
def health():
    try:
        languages = pytesseract.get_languages(config='')
        ocr = bool(languages)
    except Exception:
        languages, ocr = [], False
    return {'status':'ok' if ocr else 'degraded','ocr_available':ocr,'ocr_languages':languages,
            'extraction_mode':os.getenv('EXTRACTION_MODE','auto'),
            'token_model_configured':bool(os.getenv('TOKEN_MODEL_PATH')),
            'token_model_name':Path(os.getenv('TOKEN_MODEL_PATH','')).name if os.getenv('TOKEN_MODEL_PATH') else None,
            'time':time.time()}

@app.get('/sample-fields')
def sample_fields():
    return {'fields':list(FIELD_QUESTIONS)}

def classify(text):
    text = text.lower()
    if 'statement' in text and any(t in text for t in ('balance','account','debit')):
        return 'bank_statement'
    if 'invoice' in text:
        return 'invoice'
    if 'receipt' in text:
        return 'receipt'
    if 'report' in text:
        return 'financial_report'
    return 'unknown'

def process(raw, filename):
    if not pipeline_lock.acquire(blocking=False):
        raise HTTPException(503,'Another document is processing. Please retry shortly.')
    started=time.perf_counter()
    document_id=uuid.uuid4().hex
    try:
        try:
            packets=load_document(raw,filename,force_ocr=os.getenv('TEXT_EXTRACTION_MODE','auto')=='ocr')
        except Exception as exc:
            logging.exception('Document decoding failed')
            raise HTTPException(400,'Unable to decode document. Check file contents, limits and PDF dependencies.') from exc
        output=[]
        previous_invoice=None
        previous_columns=None
        previous_size=None
        for index,packet in enumerate(packets,1):
            if packet['tokens'] is not None:
                clean=packet['image']
                tokens=packet['tokens']
            else:
                clean=preprocess_page(packet['image'])
                try:
                    tokens=tokens_to_dicts(run_ocr(clean))
                except Exception as exc:
                    logging.exception('OCR failed')
                    raise HTTPException(503,'OCR unavailable or timed out. Check Tesseract and language packs.') from exc
            text=tokens_to_text(tokens)
            diagnostics={'text_source':packet['text_source']}
            fields=extract_fields(clean,text,tokens,diagnostics=diagnostics)
            invoice=fields.get('invoice_number',{}).get('value')
            continuing=previous_invoice and ((invoice and invoice==previous_invoice) or (not invoice and CONTINUED.search(text)))
            inherited=None
            if continuing and previous_columns and previous_size:
                inherited={key:value*clean.width/previous_size[0] for key,value in previous_columns.items()}
            geometry_items,columns=extract_items(tokens,inherited)
            native_items=pdf_table_items(packet.get('tables',[]))
            items=native_items or geometry_items
            fields=reconcile_candidates(fields,items)
            previous_invoice=invoice or (previous_invoice if continuing else None)
            previous_columns=columns
            previous_size=clean.size
            warnings=sorted({warning for value in fields.values() for warning in value.get('warnings',[])})
            kind=classify(text)
            if continuing and kind=='unknown' and output:
                kind=output[-1]['document_type']
            if kind in ('bank_statement','financial_report'):
                applicable={'vendor_name','ifsc'} if kind=='bank_statement' else {'vendor_name'}
                for name,data in fields.items():
                    if name not in applicable:
                        data.update({'value':None,'source':'not_applicable','review_required':False,'applicable':False})
                warnings.append('Transaction/report tables use inspectable heuristics. Verify columns against the page.')
            transactions,balance_checks=statement_transactions(tokens) if kind=='bank_statement' else ([],[])
            metrics=report_metrics(tokens) if kind=='financial_report' else []
            page={'page':index,'document_type':kind,'fields':fields,'line_items':items,
                  'transactions':transactions,'balance_checks':balance_checks,'financial_metrics':metrics,
                  'extraction_diagnostics':diagnostics,'relations':spatial_relations(fields,tokens),
                  'validation':validate_document(kind,fields,items,transactions,balance_checks,metrics),
                  'ocr_text':text,'ocr_tokens':tokens,'ocr_token_count':len(tokens),
                  'text_source':packet['text_source'],'image_size':list(clean.size),'warnings':warnings,
                  'preview_available':True}
            page['review_reasons']=review_reasons(page)
            if any(reason['code'] in ('conflicting_or_invalid_field','low_ocr_quality','unreadable_page') for reason in page['review_reasons']):
                page['validation']['status']='review_needed'
            storage.save_preview(document_id,index,clean)
            output.append(page)
        summary=summarize(output)
        result={'id':document_id,'filename':filename,'source_sha256':hashlib.sha256(raw).hexdigest(),
                'created_at':datetime.now(timezone.utc).isoformat(),'num_pages':len(output),'pages':output,
                'document_summary':summary,'status':summary['status'],'processing_seconds':round(time.perf_counter()-started,2)}
        storage.save(result)
        return result
    finally:
        pipeline_lock.release()

async def read_upload(file):
    filename = Path((file.filename or '').replace('\\','/')).name
    if Path(filename).suffix.lower() not in {'.pdf','.png','.jpg','.jpeg','.tif','.tiff'}:
        raise HTTPException(400,'Upload PDF, PNG, JPEG or TIFF.')
    raw = await file.read(MAX_BYTES + 1)
    await file.close()
    if not raw:
        raise HTTPException(400,'The uploaded file is empty.')
    if len(raw)>MAX_BYTES:
        raise HTTPException(413,'Document exceeds upload size limit.')
    return raw,filename

@app.post('/extract')
async def extract(file:UploadFile=File(...)):
    raw,name = await read_upload(file)
    return await run_in_threadpool(process,raw,name)

@app.post('/extract-to-excel')
async def extract_to_excel(file:UploadFile=File(...)):
    result = await extract(file)
    return Response(excel_bytes(result),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition':'attachment; filename="extracted.xlsx"'})

@app.get('/documents')
def documents(q:str='',limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0)):
    return {'documents':storage.listing(q,limit,offset)}

def require_document(document_id):
    result = storage.get(document_id)
    if result is None:
        raise HTTPException(404,'Document not found')
    return result

@app.get('/documents/{document_id}')
def document(document_id:str):
    return require_document(document_id)

@app.get('/documents/{document_id}/excel')
def document_excel(document_id:str):
    return Response(excel_bytes(require_document(document_id)),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition':'attachment; filename="extracted.xlsx"'})

class Correction(BaseModel):
    page:int=Field(ge=1)
    fields:dict[str,str|None]=Field(default_factory=dict)
    line_items:list[dict[str,Any]]|None=None
    transactions:list[dict[str,Any]]|None=None

@app.patch('/documents/{document_id}')
def correct_document(document_id:str, correction:Correction):
    result = require_document(document_id)
    if correction.page > len(result['pages']):
        raise HTTPException(400,'Page does not exist')
    if set(correction.fields)-set(FIELD_QUESTIONS):
        raise HTTPException(400,'Unknown field name')
    page = result['pages'][correction.page-1]
    for key,value in correction.fields.items():
        previous = page['fields'][key]
        page['fields'][key] = {'value':value,'confidence':None,'source':'human_review',
                               'original':previous.get('original',previous),'boxes':evidence(value,page.get('ocr_tokens',[])),'review_required':False}
    if correction.line_items is not None:
        page.setdefault('original_line_items',page['line_items'])
        page['line_items'] = correction.line_items
    if correction.transactions is not None:
        try:
            from .validation import money
        except ImportError:
            from validation import money
        for row in correction.transactions:
            if any(row.get(field) is not None and money(row[field]) is None for field in ('debit','credit','balance')):
                raise HTTPException(400,'Transaction amounts must be numeric or empty')
        page.setdefault('original_transactions',page.get('transactions',[]))
        page['transactions']=correction.transactions
        checks=[]
        for before,after in zip(correction.transactions,correction.transactions[1:]):
            opening,closing=money(before.get('balance')),money(after.get('balance'))
            debit,credit=money(after.get('debit')),money(after.get('credit'))
            if opening is not None and closing is not None and (debit is not None or credit is not None):
                expected=opening-(debit or 0)+(credit or 0)
                checks.append({'rule':'previous balance - debit + credit == balance','expected':float(expected),
                               'actual':float(closing),'passed':abs(expected-closing)<=money('0.01')})
        page['balance_checks']=checks
    page['reviewed_at']=datetime.now(timezone.utc).isoformat()
    storage.invalidate_training_review(document_id,correction.page)
    page.pop('training_review',None)
    page['validation'] = validate_document(page.get('document_type','unknown'),page['fields'],page['line_items'],
                                           page.get('transactions'),page.get('balance_checks'),page.get('financial_metrics'))
    page['relations'] = spatial_relations(page['fields'],page.get('ocr_tokens',[]))
    page['review_reasons']=review_reasons(page)
    result['document_summary']=summarize(result['pages'])
    result['status']=result['document_summary']['status']
    result['reviewed_at'] = datetime.now(timezone.utc).isoformat()
    storage.save(result)
    return result






@app.get('/documents/{document_id}/pages/{page_number}/preview')
def page_preview(document_id:str,page_number:int):
    result=require_document(document_id)
    if not 1<=page_number<=len(result['pages']):
        raise HTTPException(404,'Page not found')
    path=storage.preview_path(result['id'],page_number)
    if not path.exists():
        raise HTTPException(404,'Preview unavailable for older result; reprocess the document')
    return FileResponse(path,media_type='image/png')

@app.post('/documents/{document_id}/pages/{page_number}/approve-training')
def approve_training(document_id:str,page_number:int):
    result=require_document(document_id)
    if not 1<=page_number<=len(result['pages']):
        raise HTTPException(404,'Page not found')
    page=result['pages'][page_number-1]
    if not page.get('reviewed_at'):
        raise HTTPException(409,'Save a human review before approving a training example')
    if page['document_type'] not in ('invoice','receipt','unknown'):
        raise HTTPException(400,'Current training labels support invoice/receipt fields only')
    if page['validation']['status']=='review_needed':
        raise HTTPException(409,'Resolve validation issues before approving this page')
    if not storage.preview_path(result['id'],page_number).exists():
        raise HTTPException(409,'Reprocess the document to create its training image')
    record=build_review(result,page)
    if record['reserved_evaluation_document']:
        raise HTTPException(409,'This invoice belongs to reserved validation/test data and cannot enter training')
    storage.save_training_review(record)
    page['training_review']={'approved_at':record['approved_at'],'ready_for_training':record['ready_for_training'],
                             'unmatched_fields':record['unmatched_fields']}
    storage.save(result)
    return page['training_review']

@app.get('/training-reviews')
def training_review_status():
    rows=storage.training_reviews()
    return {'approved_pages':len(rows),'ready_pages':sum(row['ready_for_training'] for row in rows),
            'pending_alignment_pages':sum(not row['ready_for_training'] for row in rows)}
