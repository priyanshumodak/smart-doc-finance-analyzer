"""Prefer reliable embedded PDF words; rasterize and fall back to OCR per page."""
import io
import logging
import re
from PIL import Image
try:
    from .preprocessing import load_pages,MAX_PAGES
except ImportError:
    from preprocessing import load_pages,MAX_PAGES

def load_document(raw,filename,force_ocr=False):
    if not filename.lower().endswith('.pdf'):
        return [{'image':page,'tokens':None,'text_source':'ocr','tables':[]} for page in load_pages(raw,filename)]
    if not raw.lstrip().startswith(b'%PDF-'):
        raise ValueError('Invalid PDF signature')
    import pdfplumber
    packets=[]
    with pdfplumber.open(io.BytesIO(raw)) as document:
        if not 0<len(document.pages)<=MAX_PAGES:
            raise ValueError(f'PDF must contain between 1 and {MAX_PAGES} pages')
        for page in document.pages:
            # Rendering respects CropBox. Extract only that same visible region
            # and subtract its origin when converting absolute PDF coordinates.
            crop=page.cropbox or page.bbox
            visible=(max(page.bbox[0],crop[0]),max(page.bbox[1],crop[1]),
                     min(page.bbox[2],crop[2]),min(page.bbox[3],crop[3]))
            if visible[2]<=visible[0] or visible[3]<=visible[1]:
                raise ValueError('Invalid visible PDF bounds')
            if tuple(visible)!=tuple(page.bbox):
                page=page.crop(visible)
            origin_x,origin_y=page.bbox[:2]
            if page.width<=0 or page.height<=0:
                raise ValueError('Invalid PDF dimensions')
            dpi=min(144,2200*72/max(page.width,page.height))
            image=page.to_image(resolution=dpi,antialias=True,force_mediabox=False).original.convert('RGB')
            words=page.extract_words(x_tolerance=2,y_tolerance=3,keep_blank_chars=False)
            text=' '.join(word['text'] for word in words)
            useful=sum(char.isalnum() for char in text)
            usable=len(words)>=8 and useful>=25 and '\ufffd' not in text and useful/max(1,len(text))>=.45
            # Sparse captions on a large scan are not an adequate text layer.
            image_area=sum(max(0,obj.get('width',0))*max(0,obj.get('height',0)) for obj in page.images)
            if image_area>page.width*page.height*.6 and len(words)<40:
                usable=False
            usable=usable and not force_ocr
            tokens=[]
            if usable:
                width,height=image.size
                for word in words:
                    normalized=[round(1000*(word['x0']-origin_x)/page.width),round(1000*(word['top']-origin_y)/page.height),
                                round(1000*(word['x1']-origin_x)/page.width),round(1000*(word['bottom']-origin_y)/page.height)]
                    normalized=[max(0,min(1000,v)) for v in normalized]
                    box=[round(normalized[0]*width/1000),round(normalized[1]*height/1000),
                         round(normalized[2]*width/1000),round(normalized[3]*height/1000)]
                    tokens.append({'text':word['text'],'box':box,'norm_box':normalized,'conf':None,
                                   'source':'pdf_text','confidence_kind':'not_applicable'})
            tables=[]
            if usable:
                try:
                    tables=page.extract_tables()
                except Exception:
                    logging.exception('PDF table parsing failed; word geometry remains available')
            packets.append({'image':image,'tokens':tokens if usable else None,
                            'text_source':'pdf_text' if usable else 'ocr','tables':tables,
                            'text_layer_words':len(words)})
    return packets
