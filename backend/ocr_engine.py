"""Portable multilingual OCR preserving word coordinates and confidence."""
import os
import shutil
from dataclasses import dataclass
import pytesseract

command = os.getenv('TESSERACT_CMD') or shutil.which('tesseract')
if not command and os.name == 'nt':
    candidate = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    command = candidate if os.path.isfile(candidate) else None
if command:
    pytesseract.pytesseract.tesseract_cmd = command

@dataclass
class Token:
    text: str
    box: list
    norm_box: list
    conf: float

def normalize_box(box, width, height):
    if width <= 0 or height <= 0:
        raise ValueError('Invalid page dimensions')
    return [max(0, min(1000, int(1000*v/d))) for v,d in zip(box, (width,height,width,height))]

def run_ocr(pil_img, langs=None):
    requested = (langs or os.getenv('OCR_LANGUAGES', 'eng+hin')).split('+')
    available = set(pytesseract.get_languages(config=''))
    selected = '+'.join(lang for lang in requested if lang in available)
    if not selected:
        raise RuntimeError('Requested OCR language packs are unavailable')
    data = pytesseract.image_to_data(pil_img, lang=selected, config='--psm 3',
                                    output_type=pytesseract.Output.DICT, timeout=60)
    width, height = pil_img.size
    tokens = []
    for i, raw in enumerate(data['text']):
        text, confidence = raw.strip(), float(data['conf'][i])
        if not text or confidence < 0:
            continue
        x,y,w,h = (data[key][i] for key in ('left','top','width','height'))
        box = [x,y,x+w,y+h]
        tokens.append(Token(text, box, normalize_box(box,width,height), confidence))
    return tokens

def tokens_to_dicts(tokens):
    return [vars(token) for token in tokens]
