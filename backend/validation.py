"""Decimal-based reconciliation and identifier checks; no inferred pass on missing data."""
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

def money(value):
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(',', '')
    negative = text.startswith('(') and text.endswith(')')
    text = re.sub(r'(?i)(INR|RS\.?|₹|\s)', '', text).strip('()')
    if not re.fullmatch(r'[+-]?\d+(?:\.\d+)?', text):
        return None
    try:
        result = Decimal(text)
        return -result if negative else result
    except InvalidOperation:
        return None

def _to_float(value):
    parsed = money(value)
    return float(parsed) if parsed is not None else None

def gstin_check_digit(prefix):
    factor, total = 2, 0
    for char in reversed(prefix.upper()):
        product = ALPHABET.index(char) * factor
        total += product // 36 + product % 36
        factor = 1 if factor == 2 else 2
    return ALPHABET[(36 - total % 36) % 36]

def validate_gstin(value):
    value = (value or '').strip().upper()
    return bool(re.fullmatch(r'\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]', value)
                and 1 <= int(value[:2]) <= 38 and gstin_check_digit(value[:14]) == value[-1])

def validate_date(value, allow_future=False):
    if not value:
        return {'value': None, 'valid': False, 'note': 'missing date'}
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%d %b %Y', '%d %B %Y', '%Y-%m-%d', '%d.%m.%Y'):
        try:
            parsed = datetime.strptime(str(value).strip(), fmt).date()
            valid = allow_future or parsed <= date.today()
            return {'value': parsed.isoformat(), 'valid': valid,
                    'note': '' if valid else 'future invoice date'}
        except ValueError:
            pass
    return {'value': value, 'valid': False, 'note': 'unrecognised date format'}

def validate_amounts(fields, line_items, tolerance=1.0):
    def amount(key):
        return money(fields.get(key, {}).get('value'))
    checks = []
    tolerance = Decimal(str(tolerance))
    def compare(rule, expected, actual):
        if expected is None or actual is None:
            checks.append({'rule': rule, 'passed': None, 'note': 'missing evidence; not checked'})
        else:
            difference = abs(expected - actual)
            checks.append({'rule': rule, 'expected': float(expected), 'actual': float(actual),
                           'difference': float(difference), 'passed': difference <= tolerance})
    subtotal, total, tax = amount('subtotal'), amount('total_amount'), amount('tax_amount')
    components = [amount(k) for k in ('cgst', 'sgst', 'igst')]
    present = [v for v in components if v is not None]
    if tax is None and present:
        tax = sum(present, Decimal(0))
    elif tax is not None and present:
        compare('GST components == tax', sum(present, Decimal(0)), tax)
    discount, rounding = amount('discount') or Decimal(0), amount('round_off') or Decimal(0)
    compare('subtotal + tax - discount + round_off == total',
            subtotal + tax - discount + rounding if subtotal is not None and tax is not None else None, total)
    def row_expected(item):
        qty,rate=(money(item.get(name)) for name in ('qty','rate'))
        if qty is None or rate is None:
            return None,None
        net=qty*rate
        discount_text=str(item.get('discount') or '').strip()
        discount=money(discount_text.replace('%','')) if discount_text else None
        if discount is not None:
            net-=net*discount/100 if '%' in discount_text else discount
        tax_text=str(item.get('tax') or '').strip()
        tax_rate=money(tax_text.replace('%','')) if '%' in tax_text else None
        gross=net*(1+tax_rate/100) if tax_rate is not None else None
        return net,gross
    amounts=[]
    for item in line_items:
        amount=money(item.get('amount'))
        net,gross=row_expected(item)
        # Normalize a gross row only when its explicitly printed percentage
        # supports the observed amount; otherwise retain the observed value.
        inclusive=amount is not None and gross is not None and abs(gross-amount)<=tolerance and abs(net-amount)>tolerance
        item['amount_basis']='tax_inclusive' if inclusive else 'tax_exclusive_or_unconfirmed'
        amounts.append(net if inclusive else amount)
    compare('sum(line item amounts) == subtotal',
            sum(amounts, Decimal(0)) if amounts and all(v is not None for v in amounts) else None, subtotal)
    for index, item in enumerate(line_items, 1):
        qty, rate, value = (money(item.get(k)) for k in ('qty', 'rate', 'amount'))
        if qty is not None and rate is not None and value is not None:
            expected,gross=row_expected(item)
            inclusive=gross is not None and abs(gross-value)<=tolerance and abs(expected-value)>tolerance
            if inclusive:
                expected=gross
            compare(f'row {index}: qty * rate' + (' - row discount' if item.get('discount') else '') +
                    (' + explicit row GST' if inclusive else '') + ' == amount',expected,value)
    status = 'review_needed' if any(c['passed'] is False for c in checks) else (
        'ok' if all(c['passed'] is True for c in checks) else 'insufficient_data')
    return {'checks': checks, 'status': status}

def run_validation(fields, line_items):
    value = lambda key: fields.get(key, {}).get('value')
    gstin, pan = value('gstin'), value('pan')
    amounts = validate_amounts(fields, line_items)
    date_check = validate_date(value('invoice_date')) if value('invoice_date') else None
    due = validate_date(value('due_date'), allow_future=True) if value('due_date') else None
    issues = []
    if gstin and not validate_gstin(gstin):
        issues.append('GSTIN structure, state code or checksum failed')
    if pan and not re.fullmatch(r'[A-Z]{5}\d{4}[A-Z]', pan.strip().upper()):
        issues.append('PAN format failed')
    if gstin and pan and gstin.strip().upper()[2:12] != pan.strip().upper():
        issues.append('PAN does not match GSTIN')
    if date_check and not date_check['valid']:
        issues.append('Invoice date needs review')
    if due and not due['valid']:
        issues.append('Due date could not be parsed')
    if due and date_check and due['valid'] and date_check['valid'] and due['value'] < date_check['value']:
        issues.append('Due date precedes invoice date')
    missing = [k for k in ('vendor_name', 'invoice_number', 'invoice_date', 'total_amount') if not value(k)]
    if missing:
        issues.append('Missing fields: ' + ', '.join(missing))
    status = 'review_needed' if issues or amounts['status'] == 'review_needed' else amounts['status']
    return {'status': status, 'amount_reconciliation': amounts,
            'gstin_valid': validate_gstin(gstin) if gstin else None, 'date_check': date_check,
            'due_date_check': due, 'issues': issues}
