"""Document-specific validation without imposing invoice fields on statements/reports."""
try:
    from .validation import run_validation,money
except ImportError:
    from validation import run_validation,money

def validate_document(kind,fields,line_items,transactions=None,balance_checks=None,metrics=None):
    if kind not in ('bank_statement','financial_report'):
        report=run_validation(fields,line_items)
        report['document_schema']='invoice_or_receipt'
        return report
    issues=[]
    if kind=='bank_statement':
        checks=list(balance_checks or [])
        if not transactions:
            issues.append('No dated transaction rows detected')
        if not checks:
            issues.append('Not enough balance evidence to reconcile transactions')
    else:
        checks=[]
        indexed={row['label'].strip().lower():row['values'] for row in metrics or []}
        profit=next((value for key,value in indexed.items() if key.startswith('profit')),None)
        revenue=next((value for key,value in indexed.items() if key.startswith('revenue')),None)
        expenses=next((value for key,value in indexed.items() if key.startswith('expenses')),None)
        if profit and revenue and expenses:
            for period,(actual,income,cost) in enumerate(zip(profit,revenue,expenses),1):
                expected=money(income)-money(cost)
                difference=abs(expected-money(actual))
                checks.append({'rule':f'period {period}: revenue - expenses == profit',
                               'expected':float(expected),'actual':actual,'difference':float(difference),'passed':difference<=money('1')})
        if not checks:
            issues.append('No supported financial identity has sufficient labelled values')
    status='review_needed' if any(check['passed'] is False for check in checks) else ('ok' if checks else 'insufficient_data')
    return {'document_schema':kind,'status':status,'amount_reconciliation':{'status':status,'checks':checks},
            'issues':issues,'gstin_valid':None,'date_check':None,'due_date_check':None}
