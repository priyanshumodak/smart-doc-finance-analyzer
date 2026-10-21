"""Layout-aware extraction with explicit provenance and offline OCR fallbacks."""
import os
import re
import logging
from functools import lru_cache
from PIL import Image
try:
    from .validation import money
except ImportError:
    from validation import money

MODEL_NAME = os.getenv('MODEL_NAME', 'impira/layoutlm-invoices')
FIELD_QUESTIONS = {
    'vendor_name': 'What is the vendor or seller name?',
    'invoice_number': 'What is the invoice number?',
    'invoice_date': 'What is the invoice date?',
    'gstin': 'What is the seller GSTIN number?', 'pan': 'What is the seller PAN number?',
    'total_amount': 'What is the grand total amount?', 'subtotal': 'What is the subtotal?',
    'tax_amount': 'What is the total tax amount?', 'due_date': 'What is the due date?',
    'bill_to': 'Who is the document billed to?', 'place_of_supply': 'What is the place of supply?',
    'cgst': 'What is the CGST amount?', 'sgst': 'What is the SGST amount?',
    'igst': 'What is the IGST amount?', 'discount': 'What is the discount amount?',
    'round_off': 'What is the round off amount?', 'ifsc': 'What is the IFSC code?',
}
LABELS = {
    'vendor_name': r'(?:vendor|seller|supplier)(?:\s+name)?\s*:',
    'invoice_number': r'(?:invoice|inv\.?|bill)\s*(?:no\.?|number|#)',
    'invoice_date': r'(?:invoice\s+date|date\s+of\s+issue|issue\s+date|(?<!due )\bdate)',
    'due_date': r'due\s+date', 'bill_to': r'(?:bill(?:ed)?\s+to|buyer)',
    'place_of_supply': r'place\s+of\s+supply',
    'subtotal': r'(?:sub\s*total|taxable\s+(?:amount|value))',
    'tax_amount': r'(?:total\s+(?:tax|gst)|(?:gst|tax)\s+total|tax\s+amount|(?<![A-Z])GST\b)(?:\s*\([^)]*\))?',
    'total_amount': r'(?:grand\s+total|net\s+(?:amount|payable)|amount\s+due|(?<!sub)(?<!GST )(?<!Tax )\btotal(?!\s+(?:tax|gst)\b))',
    'cgst': r'\bCGST(?:\s*\([^)]*\)|\s+\d+(?:\.\d+)?%)?',
    'sgst': r'\bSGST(?:\s*\([^)]*\)|\s+\d+(?:\.\d+)?%)?',
    'igst': r'\bIGST(?:\s*\([^)]*\)|\s+\d+(?:\.\d+)?%)?',
    'discount': r'discount(?:\s*\([^)]*\))?', 'round_off': r'round\s*off',
}
INDIA_REGEX = {
    'gstin': re.compile(r'\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[A-Z0-9]\b', re.I),
    'pan': re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b', re.I),
    'ifsc': re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b', re.I),
}

@lru_cache(maxsize=1)
def get_pipeline():
    try:
        from transformers import pipeline
        return pipeline('document-question-answering', model=MODEL_NAME)
    except Exception:
        logging.exception('LayoutLM QA unavailable; using labelled OCR fallback')
        return None

@lru_cache(maxsize=1)
def get_token_model():
    from transformers import AutoProcessor, AutoModelForTokenClassification
    path = os.environ['TOKEN_MODEL_PATH']
    processor = AutoProcessor.from_pretrained(path, apply_ocr=False)
    model = AutoModelForTokenClassification.from_pretrained(path)
    import torch
    device=os.getenv('INFERENCE_DEVICE','auto')
    if device=='auto':
        device='cuda' if torch.cuda.is_available() else 'cpu'
    model.to(device)
    model.eval()
    return processor, model

def token_fields(image, tokens, runtime=None):
    """Decode BIO spans using original word IDs, retaining boxes and model scores."""
    import torch
    processor, model = get_token_model()
    if runtime is not None:
        runtime['device']=str(model.device)
    words = [t['text'] for t in tokens]
    if not words:
        return {}
    results = {}
    # Keep every word; explicit chunks avoid silent 512-token truncation.
    try:
        from .token_windows import word_windows
    except ImportError:
        from token_windows import word_windows
    for start,end in word_windows(words,[token['norm_box'] for token in tokens],processor.tokenizer,512):
        subset = tokens[start:end]
        encoded = processor(image, [t['text'] for t in subset], boxes=[t['norm_box'] for t in subset],
                            truncation=True, padding='max_length', max_length=512, return_tensors='pt')
        ids = encoded.word_ids(batch_index=0)
        represented = {i for i in ids if i is not None}
        if len(represented) < len(subset):
            raise ValueError('Token chunk exceeds model context; use shorter OCR words/chunks')
        with torch.no_grad():
            probabilities = model(**{key:value.to(model.device) for key,value in encoded.items()}).logits.softmax(-1)[0].cpu()
        seen, spans, active = set(), [], None
        for position, word_id in enumerate(ids):
            if word_id is None or word_id in seen:
                continue
            seen.add(word_id)
            score, label_id = probabilities[position].max(-1)
            label = model.config.id2label[int(label_id)]
            if label == 'O' or '-' not in label:
                active = None
                continue
            prefix, name = label.split('-', 1)
            name = name.lower()
            if name not in FIELD_QUESTIONS:
                active = None
                continue
            token = subset[word_id]
            if prefix == 'B' or active is None or active['field'] != name:
                active = {'field': name, 'words': [], 'scores': [], 'boxes': []}
                spans.append(active)
            active['words'].append(token['text'])
            active['scores'].append(float(score))
            active['boxes'].append(token['box'])
        for span in spans:
            score = sum(span['scores']) / len(span['scores'])
            field = span['field']
            if score > results.get(field, {}).get('confidence', 0):
                results[field] = {'value': ' '.join(span['words']), 'confidence': round(score, 4),
                                  'source': 'layoutlmv3_token', 'boxes': span['boxes']}
    return results

def extract_fields(pil_img: Image.Image, ocr_text='', tokens=None, diagnostics=None):
    try:
        from .candidates import rule_candidates,candidate,fuse
    except ImportError:
        from candidates import rule_candidates,candidate,fuse
    tokens=tokens or []
    diagnostics=diagnostics if diagnostics is not None else {}
    mode=os.getenv('EXTRACTION_MODE','auto').lower()
    diagnostics.update({'mode':mode,'token_model':{'status':'not_requested'}})
    warnings=[]
    policy=os.getenv('CANDIDATE_POLICY','combined')
    pools={} if policy=='model_only' else rule_candidates(ocr_text,tokens,LABELS,INDIA_REGEX)
    diagnostics['candidate_policy']=policy
    if os.getenv('TOKEN_MODEL_PATH') and mode!='ocr':
        try:
            runtime={}
            predictions=token_fields(pil_img,tokens,runtime=runtime)
            threshold=float(os.getenv('TOKEN_MIN_CONFIDENCE','0.5'))
            accepted=0
            for field,data in predictions.items():
                item=candidate(field,data['value'],'layoutlmv3_token',data['confidence'],tokens)
                item['boxes']=data.get('boxes') or item['boxes']
                if data['confidence']<threshold:
                    item['eligible']=False
                    item['reasons'].append('Below configured model confidence threshold')
                else:
                    accepted+=1
                pools.setdefault(field,[]).append(item)
            diagnostics['token_model']={'status':'executed','model_name':os.path.basename(os.environ['TOKEN_MODEL_PATH']),'device':runtime.get('device'),'predicted_fields':len(predictions),'accepted_fields':accepted,'minimum_confidence':threshold}
            if accepted<len(predictions):
                warnings.append('Low-confidence token predictions omitted; labelled OCR fallback used')
        except Exception:
            logging.exception('Token classification failed')
            diagnostics['token_model']={'status':'failed'}
            warnings.append('Token model unavailable; OCR fallback used')
    elif mode!='ocr':
        qa=get_pipeline()
        if qa is None:
            warnings.append('LayoutLM QA unavailable; OCR fallback used')
        else:
            for field,question in FIELD_QUESTIONS.items():
                try:
                    kwargs={'image':pil_img,'question':question,'top_k':1}
                    if tokens:
                        kwargs['word_boxes']=[(t['text'],t['norm_box']) for t in tokens]
                    answer=qa(**kwargs)
                    answer=answer[0] if isinstance(answer,list) and answer else answer
                    if isinstance(answer,dict) and answer.get('answer'):
                        item=candidate(field,answer['answer'],'layoutlm_qa',float(answer.get('score',0)),tokens)
                        item['eligible']=item['confidence']>=.35
                        pools.setdefault(field,[]).append(item)
                except Exception:
                    logging.exception('QA inference failed for %s',field)
                    warnings.append(f'Model inference failed for {field}; OCR fallback used')
    results=fuse(pools,FIELD_QUESTIONS)
    diagnostics['selection_policy']='independent candidates, format checks and source ranking'
    for value in results.values():
        if warnings:
            value['warnings']=sorted(set(warnings))
    return results

def group_rows(tokens, y_tolerance=8):
    rows = []
    for token in sorted(tokens, key=lambda t: (t['box'][1], t['box'][0])):
        center = (token['box'][1] + token['box'][3]) / 2
        if rows and abs(center - rows[-1]['y']) <= max(y_tolerance, (token['box'][3]-token['box'][1])*0.5):
            rows[-1]['tokens'].append(token)
        else:
            rows.append({'y': center, 'tokens': [token]})
    return [sorted(row['tokens'], key=lambda t: t['box'][0]) for row in rows]

def tokens_to_text(tokens):
    return '\n'.join(' '.join(t['text'] for t in row) for row in group_rows(tokens))

def extract_line_items(tokens, y_tolerance=8):
    items, in_table = [], False
    for row in group_rows(tokens, y_tolerance):
        texts = [t['text'] for t in row]
        raw = ' '.join(texts)
        if re.search(r'\b(?:qty|quantity)\b', raw, re.I) and re.search(r'\b(?:amount|total|rate|price)\b', raw, re.I):
            in_table = True
            continue
        if re.match(r'^(?:sub\s*total|grand\s+total|total|taxable|[CS I]*GST|discount|round\s*off)\b', raw, re.I):
            in_table = False
            continue
        if not in_table:
            continue
        # Parse trailing columns only; numbers inside descriptions remain intact.
        tail = []
        for text in reversed(texts):
            parsed = money(text)
            if parsed is None:
                break
            tail.insert(0, parsed)
        if len(tail) < 3:
            continue
        qty, rate, amount = tail[-3:]
        description = ' '.join(texts[:-len(tail)])
        if not description:
            continue
        items.append({'description': description, 'qty': float(qty), 'rate': float(rate),
                      'amount': float(amount), 'raw_row': raw, 'source': 'ocr_table_heuristic',
                      'amount_candidates': [str(v) for v in tail],
                      'box': [min(t['box'][0] for t in row), min(t['box'][1] for t in row),
                              max(t['box'][2] for t in row), max(t['box'][3] for t in row)]})
    return items
