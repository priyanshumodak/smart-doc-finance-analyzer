"""Choose a complete OCR pass by source quality, never by reference answers."""
import re
try:
    from .ocr_engine import tokens_to_dicts
except ImportError:
    from ocr_engine import tokens_to_dicts


def score(tokens):
    good=[t for t in tokens if t['conf']>=35 and re.search(r'[A-Za-z0-9]',t['text'])]
    coverage=sum(min(len(t['text']),120 if ' ' in t['text'] else 18)*(t['conf']/100) for t in good)
    try:
        from .layout_extractor import group_rows
    except ImportError:
        from layout_extractor import group_rows
    label_rows=sum(bool(re.search(r'(?i)\b(?:sub[ -]?total|total|pajak|ppn|pb[1il]|tax|tunai|cash|change|kembali)\b',text) and re.search(r'\d[\d.,]{2,}',text)) for text in (' '.join(t['text'] for t in row) for row in group_rows(good)))
    return coverage+20*label_rows


def recognize(image, ocr, preprocess, neural=False):
    from PIL import Image
    raw=image.copy()
    scale=min(720/min(raw.size),2600/max(raw.size))
    if scale>1:
        raw=raw.resize((round(raw.width*scale),round(raw.height*scale)),Image.Resampling.LANCZOS)
    raw.thumbnail((2600,2600))
    processed=preprocess(raw)
    variants=[]
    if neural:
        try:
            try:
                from .neural_ocr import recognize as neural_recognize
            except ImportError:
                from neural_ocr import recognize as neural_recognize
            neural_page=image.copy() if image.height>2400 and image.height>image.width*2 else raw
            neural_tokens=tokens_to_dicts(neural_recognize(neural_page))
            if neural_tokens:
                variants.append((score(neural_tokens),neural_page,neural_tokens,{'variant':'neural_ppocrv6','engine':'RapidOCR/PP-OCRv6','box_granularity':'line','tokens':len(neural_tokens),'quality_score':round(score(neural_tokens),2)}))
        except Exception:
            pass  # Source-only Tesseract passes remain available if neural inference fails.
    passes=[('original_auto',raw,3)] if variants else [('processed_auto',processed,3),('original_auto',raw,3),('original_block',raw,6),('processed_block',processed,6)]
    for name,page,psm in passes:
        try:
            tokens=tokens_to_dicts(ocr(page,psm=psm))
            variants.append((score(tokens),page,tokens,{'variant':name,'psm':psm,'tokens':len(tokens),'quality_score':round(score(tokens),2)}))
        except Exception:
            if not variants and name=='processed_block': raise
    if not variants: raise RuntimeError('All OCR passes failed')
    best=max(variants,key=lambda row:row[0])
    return best[1],best[2],{'selected':best[3],'passes':[r[3] for r in variants],
                         'policy':'Maximize confidence-weighted source text coverage; no dataset labels used'}
