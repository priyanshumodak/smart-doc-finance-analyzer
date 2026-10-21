import unittest
from backend.document_tables import statement_transactions, report_metrics, spatial_relations
from backend.layout_extractor import extract_fields
from backend.document_validation import validate_document
from PIL import Image
from unittest.mock import patch
import os

class DocumentTableTests(unittest.TestCase):
    def tokens(self,rows):
        return [{'text':word,'box':[x,y*30,x+60,y*30+20],'norm_box':[x,y*30,x+60,y*30+20]}
                for y,row in enumerate(rows) for x,word in row]

    def test_statement_balance_transition(self):
        tokens=self.tokens([[(0,'Date'),(300,'Debit'),(450,'Credit'),(600,'Balance')],
                            [(0,'01/01/2020'),(100,'Opening'),(600,'1000.00')],
                            [(0,'02/01/2020'),(100,'Shop'),(300,'200.00'),(600,'800.00')]])
        transactions,checks=statement_transactions(tokens)
        self.assertEqual(len(transactions),2)
        self.assertEqual(transactions[1]['debit'],200)
        self.assertTrue(checks[0]['passed'])

    def test_statement_validation_does_not_require_invoice_fields(self):
        report=validate_document('bank_statement',{},[],[{'date':'01/01/2020'}],[{'rule':'balance','passed':True}],[])
        self.assertEqual(report['status'],'ok')
        self.assertEqual(report['issues'],[])

    def test_report_profit_reconciliation(self):
        rows=[{'label':'Revenue','values':[100]},{'label':'Expenses','values':[60]},{'label':'Profit','values':[40]}]
        self.assertEqual(validate_document('financial_report',{},[],metrics=rows)['status'],'ok')
        rows[-1]['values']=[30]
        self.assertEqual(validate_document('financial_report',{},[],metrics=rows)['status'],'review_needed')

    def test_report_numeric_rows(self):
        metrics=report_metrics(self.tokens([[(0,'Revenue'),(300,'1,000.00'),(450,'900.00')]]))
        self.assertEqual(metrics[0]['values'],[1000,900])

    def test_relations_are_explicitly_heuristic(self):
        links=spatial_relations({'vendor_name':{'value':'Seller'}},self.tokens([[(0,'Vendor:'),(100,'Seller')]]))
        self.assertFalse(links[0]['learned_relation'])

    def test_seller_identifiers_are_not_vendor_and_total_gst_is_not_grand_total(self):
        with patch.dict(os.environ,{'EXTRACTION_MODE':'ocr'}):
            fields=extract_fields(Image.new('RGB',(10,10)),
                                  'Sample Seller Ltd\nSeller GSTIN: 27ABCDE1234F1Z0\nTotal GST: 18.00\nGrand Total: 118.00')
        self.assertEqual(fields['vendor_name']['value'],'Sample Seller Ltd')
        self.assertEqual(fields['total_amount']['value'],'118.00')

    def test_gstin_is_not_tax_amount(self):
        with patch.dict(os.environ,{'EXTRACTION_MODE':'ocr'}):
            fields=extract_fields(Image.new('RGB',(10,10)),'GSTIN: 27ABCDE1234F1Z0\nSubtotal: 100\nGST (18%): Rs.18\nTotal: 118')
        self.assertEqual(fields['tax_amount']['value'],'Rs.18')

if __name__=='__main__':
    unittest.main()
