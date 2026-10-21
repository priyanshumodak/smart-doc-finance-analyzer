"""Inspectable spatial key/value links and statement/report table heuristics."""
import re
try:
    from .layout_extractor import group_rows
    from .validation import money
    from .relation_model import union, score_relation
except ImportError:
    from layout_extractor import group_rows
    from validation import money
    from relation_model import union, score_relation

DATE = re.compile(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$')

def spatial_relations(fields,tokens):
    links = []
    rows = group_rows(tokens)
    for field,data in fields.items():
        value = str(data.get('value') or '').strip()
        if not value:
            continue
        for row in rows:
            text = ' '.join(t['text'] for t in row)
            if value.casefold() not in text.casefold():
                continue
            position=text.casefold().find(value.casefold())
            offset=0
            keys,values=[],[]
            for token in row:
                start,end=offset,offset+len(token['text'])
                if end<=position:
                    keys.append(token)
                elif start<position+len(value) and end>position:
                    values.append(token)
                offset=end+1
            confidence=None
            if keys and values and all('norm_box' in token for token in keys+values):
                confidence=score_relation(union([token['norm_box'] for token in keys]),union([token['norm_box'] for token in values]))
            links.append({'confidence':round(confidence,4) if confidence is not None else None,
                          'candidate_accepted':confidence>=.5 if confidence is not None else None,
                          'scorer':'spatial_logistic_regression' if confidence is not None else None,
                          'field':field,'value':value,'row_text':text,
                          'box':[min(t['box'][0] for t in row),min(t['box'][1] for t in row),
                                 max(t['box'][2] for t in row),max(t['box'][3] for t in row)],
                          'method':'same_row_value_match','learned_relation':False})
            break
    return links

def statement_transactions(tokens):
    """Require named debit/credit/balance columns; preserve ambiguity instead of inventing values."""
    headers,transactions = {},[]
    for row in group_rows(tokens):
        for token in row:
            name = token['text'].lower().strip(':')
            if name in ('debit','withdrawal','withdrawals'):
                headers['debit'] = token['box'][0]
            elif name in ('credit','deposit','deposits'):
                headers['credit'] = token['box'][0]
            elif name == 'balance':
                headers['balance'] = token['box'][0]
        if not headers or not row or not DATE.match(row[0]['text']):
            continue
        transaction = {'date':row[0]['text'],'description':'','debit':None,'credit':None,'balance':None,
                       'source':'header_position_heuristic'}
        words = []
        for token in row[1:]:
            numeric = money(token['text'])
            if numeric is not None and token['box'][0] >= min(headers.values())-40:
                column = min(headers,key=lambda k:abs(headers[k]-token['box'][0]))
                if transaction[column] is None:
                    transaction[column] = float(numeric)
                else:
                    words.append(token['text'])
            else:
                words.append(token['text'])
        transaction['description'] = ' '.join(words)
        transactions.append(transaction)
    checks = []
    for previous,current in zip(transactions,transactions[1:]):
        if previous['balance'] is None or current['balance'] is None:
            continue
        if current['debit'] is None and current['credit'] is None:
            continue
        expected = money(previous['balance']) - (money(current['debit']) or 0) + (money(current['credit']) or 0)
        actual = money(current['balance'])
        checks.append({'rule':'previous balance - debit + credit == balance','date':current['date'],
                       'expected':float(expected),'actual':float(actual),'passed':abs(expected-actual)<=money('0.01')})
    return transactions,checks

def report_metrics(tokens):
    metrics=[]
    for row in group_rows(tokens):
        text=' '.join(t['text'] for t in row)
        if not re.search(r'\b(revenue|profit|income|assets|liabilities|expenses|cash)\b',text,re.I):
            continue
        values=[float(value) for token in row if (value:=money(token['text'])) is not None]
        if values:
            metrics.append({'label':' '.join(t['text'] for t in row if money(t['text']) is None),
                            'values':values,'source':'financial_row_heuristic','raw_row':text})
    return metrics
