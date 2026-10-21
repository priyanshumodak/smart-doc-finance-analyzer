"""Header-driven invoice tables with additional columns and wrapped descriptions."""
import re
try:
    from .layout_extractor import group_rows
    from .validation import money
except ImportError:
    from layout_extractor import group_rows
    from validation import money

ALIASES={'qty':{'qty','quantity'},'rate':{'rate','price','unitprice'},'amount':{'amount','amt','total','value','netamount'},
         'hsn':{'hsn','sac','hsn/sac'},'discount':{'discount','disc'},'tax':{'gst','tax','vat'}}
STOP=re.compile(r'^(?:sub\s*total|grand\s+total|total\b|taxable|[CSI]GST\b|gst\b|discount\b|round\s*off|amount\s+due|bank\b|terms\b|thank\b)',re.I)

def normalize(text):
    return re.sub(r'[^a-z/]','',text.lower())

def numeric(text,quantity=False):
    value=money(text)
    if value is None and quantity:
        match=re.fullmatch(r'\s*([\d,.]+)\s*(?:nos?\.?|pcs?\.?|units?|kg|m|sets?)\s*',text,re.I)
        value=money(match[1]) if match else None
    return float(value) if value is not None else None

def identify_header(row):
    columns={}
    for token in row:
        name=normalize(token['text'])
        for field,aliases in ALIASES.items():
            if name in aliases:
                columns[field]=token['box'][0]
    return columns if 'amount' in columns and ('qty' in columns or 'rate' in columns) else None

def extract_items(tokens,inherited_columns=None):
    items=[]
    columns=dict(inherited_columns or {})
    active=bool(columns)
    pending=''
    for row in group_rows(tokens):
        raw=' '.join(token['text'] for token in row)
        header=identify_header(row)
        if header:
            columns=header
            active=True
            pending=''
            continue
        if STOP.match(raw):
            active=False
            pending=''
            continue
        if not active or not columns:
            continue
        ordered=sorted(columns,key=lambda name:columns[name])
        first=columns[ordered[0]]
        cells={field:[] for field in columns}
        description=[]
        for token in row:
            x=(token['box'][0]+token['box'][2])/2
            if token['box'][0]<first-20:
                description.append(token['text'])
            else:
                field=min(ordered,key=lambda name:abs(x-columns[name]))
                cells[field].append(token['text'])
        values={field:' '.join(words) for field,words in cells.items()}
        amount=numeric(values.get('amount',''))
        desc=' '.join(description).strip()
        if amount is None:
            if desc and not any(values.values()):
                if items:
                    items[-1]['description']+=' '+desc
                    items[-1]['raw_row']+='\n'+raw
                else:
                    pending=(pending+' '+desc).strip()
            continue
        desc=(pending+' '+desc).strip()
        pending=''
        if not desc:
            continue
        item={'description':desc,'qty':numeric(values.get('qty',''),True),'rate':numeric(values.get('rate','')),
              'amount':amount,'source':'header_geometry','raw_row':raw,
              'box':[min(t['box'][0] for t in row),min(t['box'][1] for t in row),max(t['box'][2] for t in row),max(t['box'][3] for t in row)]}
        for optional in ('hsn','discount','tax'):
            if values.get(optional):
                item[optional]=values[optional]
        items.append(item)
    # Proportional-font OCR can shift header positions. A restricted suffix
    # fallback is useful for simple qty/rate/amount tables, never tax/discount tables.
    fallback=[]
    active=bool(inherited_columns)
    safe=not any(name in columns for name in ('tax','discount'))
    for row in group_rows(tokens):
        header=identify_header(row)
        raw=' '.join(token['text'] for token in row)
        if header:
            active=True
            safe=not any(name in header for name in ('tax','discount'))
            continue
        if STOP.match(raw):
            active=False
            continue
        if not active or not safe:
            continue
        remainder=raw
        tail=[]
        for _ in range(3):
            match=re.search(r'(?:Rs\.?|INR|₹)?\s*([-+]?\d[\d,]*(?:\.\d+)?)\s*$',remainder,re.I)
            if not match:
                break
            tail.insert(0,numeric(match[1]))
            remainder=remainder[:match.start()].rstrip()
        if len(tail)==3 and remainder:
            fallback.append({'description':remainder,'qty':tail[0],'rate':tail[1],'amount':tail[2],
                             'source':'numeric_suffix_fallback','raw_row':raw,
                             'box':[min(t['box'][0] for t in row),min(t['box'][1] for t in row),max(t['box'][2] for t in row),max(t['box'][3] for t in row)]})
    def coherent(rows):
        return sum(item.get('qty') is not None and item.get('rate') is not None and
                   abs(item['qty']*item['rate']-item['amount'])<=1 for item in rows)
    if fallback and (not items or coherent(fallback)>coherent(items)):
        items=fallback
    return items,columns

def pdf_table_items(tables):
    items=[]
    for table in tables or []:
        header=None
        for row in table:
            cells=[str(value or '').strip() for value in row]
            found={field:index for index,value in enumerate(cells) for field,aliases in ALIASES.items() if normalize(value) in aliases}
            if 'amount' in found and ('qty' in found or 'rate' in found):
                header=found
                continue
            if not header or not cells or STOP.match(cells[0]):
                continue
            amount=numeric(cells[header['amount']]) if header['amount']<len(cells) else None
            if amount is None:
                continue
            occupied=set(header.values())
            description=' '.join(value.replace('\n',' ') for index,value in enumerate(cells) if index not in occupied).strip()
            if not description:
                continue
            item={'description':description,'amount':amount,'source':'pdf_table','raw_row':' | '.join(cells)}
            for field in ('qty','rate'):
                item[field]=numeric(cells[header[field]],field=='qty') if field in header else None
            for field in ('hsn','tax','discount'):
                if field in header:
                    item[field]=cells[header[field]]
            items.append(item)
    return items
