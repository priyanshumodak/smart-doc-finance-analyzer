"""Portable trained receipt-line classifier; no Torch or network at inference."""
import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path


def features(text,y):
    words=[word for word in re.findall(r'[a-z0-9]+',text.lower()) if re.search('[a-z]',word)]
    values=Counter('w:'+word for word in words)
    for word in words:
        for n in (3,4):
            values.update('c:'+word[i:i+n] for i in range(len(word)-n+1))
    values['@bottom' if y>.6 else '@middle' if y>.3 else '@top']=1
    if '%' in text: values['@percent']=1
    if re.search(r'(?i)\brp\.?',text): values['@rupiah']=1
    return values


@lru_cache(maxsize=1)
def load():
    path=Path(__file__).parent/'assets'/'indonesian_line_model.json'
    if not path.exists(): return None
    model=json.loads(path.read_text(encoding='utf-8'))
    model['_vocabulary']=frozenset(model['vocabulary'])
    return model


def predict(text,y):
    model=load()
    if not model: return None,0.0
    vector=features(text,y)
    scores={label:model['priors'][label]+sum(count*model['weights'][label].get(feature,0) for feature,count in vector.items() if feature in model['_vocabulary']) for label in model['labels']}
    best=max(scores,key=scores.get); maximum=scores[best]
    denominator=sum(math.exp(value-maximum) for value in scores.values())
    return best,1/denominator
