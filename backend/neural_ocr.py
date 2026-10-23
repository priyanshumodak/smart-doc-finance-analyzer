"""Bundled PP-OCRv6 CPU inference with source-line evidence and bounded threads."""
from functools import lru_cache
import numpy as np
import re
try:
    from .ocr_engine import Token,normalize_box
except ImportError:
    from ocr_engine import Token,normalize_box


@lru_cache(maxsize=1)
def engine():
    from rapidocr import RapidOCR
    return RapidOCR(params={'Global.log_level':'error','EngineConfig.onnxruntime.intra_op_num_threads':2,
                            'EngineConfig.onnxruntime.inter_op_num_threads':1})


def _single(image):
    result=engine()(np.asarray(image.convert('RGB')))
    if result.boxes is None or result.txts is None: return []
    tokens=[];width,height=image.size
    geometries=[]
    for polygon in result.boxes:
        dx=float(polygon[1][0]-polygon[0][0]); dy=float(polygon[1][1]-polygon[0][1])
        center_y=sum(float(point[1]) for point in polygon)/4
        if dx>25 and abs(dy/dx)<.3: geometries.append((center_y,dy/dx))
    for polygon,text,confidence in zip(result.boxes,result.txts,result.scores):
        xs=[float(point[0]) for point in polygon]; ys=[float(point[1]) for point in polygon]
        box=[max(0,round(min(xs))),max(0,round(min(ys))),min(width,round(max(xs))),min(height,round(max(ys)))]
        token=Token(str(text),box,normalize_box(box,width,height),float(confidence)*100)
        center_y=(box[1]+box[3])/2
        nearby=sorted(geometries,key=lambda item:abs(item[0]-center_y))[:6]
        slope=float(np.median([item[1] for item in nearby])) if nearby else 0.0
        token.row_y=center_y-slope*(box[0]+box[2])/2
        token.box_granularity='line'
        tokens.append(token)
    return tokens


def recognize(image):
    if image.height<=2400 or image.height<image.width*2:
        return _single(image)
    # Keep long receipt glyphs readable instead of shrinking the whole strip.
    tokens=[];width,height=image.size
    for top in range(0,height,1600):
        bottom=min(height,top+1800)
        for token in _single(image.crop((0,top,width,bottom))):
            token.box=[token.box[0],token.box[1]+top,token.box[2],token.box[3]+top]
            token.norm_box=normalize_box(token.box,width,height)
            token.row_y+=top
            repeated=False
            for previous in tokens:
                overlap=max(0,min(token.box[3],previous.box[3])-max(token.box[1],previous.box[1]))
                if re.sub(r'\W','',previous.text).casefold()==re.sub(r'\W','',token.text).casefold() and overlap>min(token.box[3]-token.box[1],previous.box[3]-previous.box[1])*.5 and abs(token.box[0]-previous.box[0])<20:
                    repeated=True;break
            if not repeated: tokens.append(token)
        if bottom==height: break
    return tokens
