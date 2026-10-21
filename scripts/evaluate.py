"""Compare saved extraction JSON against ground truth without rewarding missing values."""
import argparse
import json
import re
from pathlib import Path

FIELDS = ['vendor_name','invoice_number','invoice_date','gstin','pan','subtotal','tax_amount','total_amount','bill_to','due_date','place_of_supply']

def normalize(value,field=None):
    if isinstance(value,dict):
        value = value.get('value')
    if value is None:
        return ''
    text = str(value).strip().casefold()
    if field in ('invoice_date','due_date'):
        from datetime import datetime
        for fmt in ('%d/%m/%Y','%d-%m-%Y','%Y-%m-%d','%d %b %Y','%d %B %Y','%d.%m.%Y'):
            try:
                return datetime.strptime(text,fmt).date().isoformat()
            except ValueError:
                pass
    if field is not None and field not in ('subtotal','tax_amount','total_amount','cgst','sgst','igst','discount','round_off'):
        return re.sub(r'\s+',' ',text)
    numeric = re.sub(r'(?:inr|rs\.?|₹|,|\s)', '', text)
    try:
        from decimal import Decimal
        return str(Decimal(numeric).normalize())
    except Exception:
        return re.sub(r'\s+',' ',text)

def evaluate(truth, predictions):
    indexed = {}
    for prediction in predictions:
        key = prediction.get('invoice_number') or Path(prediction.get('filename','')).stem
        fields = prediction.get('fields',prediction)
        if prediction.get('pages'):
            fields = prediction['pages'][0]['fields']
        indexed[str(key)] = fields
    totals = {field:{'tp':0,'fp':0,'fn':0,'correct':0,'support':0} for field in FIELDS}
    for record in truth:
        keys = [str(record.get('invoice_number','')),Path(record.get('image_path','')).stem]
        predicted = next((indexed[key] for key in keys if key in indexed),{})
        for field in FIELDS:
            if record.get('annotated_fields') is not None and field not in record['annotated_fields']:
                continue
            expected, actual = normalize(record.get(field),field),normalize(predicted.get(field),field)
            score = totals[field]
            if expected:
                score['support'] += 1
                if actual==expected:
                    score['tp'] += 1
                    score['correct'] += 1
                else:
                    score['fn'] += 1
                    score['fp'] += bool(actual)
            elif actual:
                score['fp'] += 1
    def metrics(score):
        tp,fp,fn = (score[k] for k in ('tp','fp','fn'))
        precision = tp/(tp+fp) if tp+fp else 0
        recall = tp/(tp+fn) if tp+fn else 0
        return {**score,'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0,
                'accuracy':score['correct']/score['support'] if score['support'] else None}
    micro = {key:sum(score[key] for score in totals.values()) for key in ('tp','fp','fn','correct','support')}
    return {'documents':len(truth),'fields':{key:metrics(score) for key,score in totals.items()},'micro':metrics(micro),
            'scope':'Document field exact match after normalization. Not token BIO F1 or relation F1. First-page fields only. Explicit annotation masks exclude unknown fields.'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--truth',required=True)
    parser.add_argument('--predictions',required=True,help='JSON array or directory containing extraction JSON files')
    parser.add_argument('--output',default='evaluation.json')
    args = parser.parse_args()
    truth = json.loads(Path(args.truth).read_text(encoding='utf-8-sig'))
    source = Path(args.predictions)
    if source.is_dir():
        predictions = [json.loads(p.read_text(encoding='utf-8-sig')) for p in source.glob('*.json')]
    else:
        predictions = json.loads(source.read_text(encoding='utf-8-sig'))
        if isinstance(predictions,dict):
            predictions = [predictions]
    report = evaluate(truth,predictions)
    Path(args.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report['micro'],indent=2))

if __name__=='__main__':
    main()
