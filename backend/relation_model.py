"""Small learned spatial relation scorer stored as inspectable JSON, without pickle."""
import json
import math
import os
from functools import lru_cache
from pathlib import Path

def features(key,value):
    kx,ky=(key[0]+key[2])/2,(key[1]+key[3])/2
    vx,vy=(value[0]+value[2])/2,(value[1]+value[3])/2
    dx,dy=(vx-kx)/1000,(vy-ky)/1000
    return [dx,dy,abs(dx),abs(dy),math.hypot(dx,dy),float(abs(dy)<.015),
            (key[2]-key[0])/1000,(value[2]-value[0])/1000]

def union(boxes):
    return [min(box[0] for box in boxes),min(box[1] for box in boxes),max(box[2] for box in boxes),max(box[3] for box in boxes)]

@lru_cache(maxsize=1)
def load_model(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def score_relation(key,value,path=None):
    path=path or os.getenv('RELATION_MODEL_PATH')
    if not path:
        return None
    model=load_model(path)
    values=features(key,value)
    score=model['intercept']+sum(weight*(value-mean)/scale for value,mean,scale,weight in zip(values,model['mean'],model['scale'],model['coefficients']))
    return 1/(1+math.exp(-max(-50,min(50,score))))
