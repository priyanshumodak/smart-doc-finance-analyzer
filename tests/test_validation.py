import unittest
from backend.validation import money, validate_amounts, validate_gstin, gstin_check_digit, run_validation
from scripts.evaluate import evaluate

class ValidationTests(unittest.TestCase):
    def fields(self,**values):
        return {key:{'value':value} for key,value in values.items()}

    def test_signed_indian_currency(self):
        self.assertEqual(str(money('Rs. 1,23,456.78')),'123456.78')
        self.assertEqual(str(money('(1,200.00)')),'-1200.00')
        self.assertIsNone(money('not 123 valid'))

    def test_real_line_sum_and_mismatch(self):
        fields = self.fields(subtotal='300',tax_amount='54',total_amount='354')
        self.assertEqual(validate_amounts(fields,[{'amount':100},{'amount':200}])['status'],'ok')
        report = validate_amounts(fields,[{'amount':100},{'amount':180}])
        self.assertEqual(report['status'],'review_needed')
        self.assertEqual(report['checks'][1]['expected'],280)

    def test_missing_evidence_does_not_pass(self):
        self.assertEqual(validate_amounts({},[])['status'],'insufficient_data')

    def test_tax_components_not_double_counted(self):
        fields = self.fields(subtotal=100,cgst=9,sgst=9,tax_amount=18,total_amount=118)
        self.assertEqual(validate_amounts(fields,[{'amount':100}])['status'],'ok')

    def test_checksum_and_pan(self):
        prefix = '27ABCDE1234F1Z'
        value = prefix+gstin_check_digit(prefix)
        self.assertTrue(validate_gstin(value))
        self.assertFalse(validate_gstin(value[:-1]+('0' if value[-1]!='0' else '1')))
        report = run_validation(self.fields(gstin=value,pan='AAAAA1234A'),[])
        self.assertIn('PAN does not match GSTIN',report['issues'])

    def test_due_date_can_be_future(self):
        report = run_validation(self.fields(invoice_date='01/01/2020',due_date='01/01/2099'),[])
        self.assertTrue(report['due_date_check']['valid'])

    def test_wrong_prediction_counts_fp_and_fn(self):
        report = evaluate([{'invoice_number':'A','vendor_name':'Seller'}],[{'invoice_number':'A','vendor_name':'Wrong'}])
        score = report['fields']['vendor_name']
        self.assertEqual((score['tp'],score['fp'],score['fn']),(0,1,1))

    def test_partial_annotations_do_not_penalize_unknown_fields(self):
        report=evaluate([{'invoice_number':'A','total_amount':100,'annotated_fields':['total_amount']}],
                        [{'invoice_number':'A','total_amount':100,'vendor_name':'Unannotated Seller'}])
        self.assertEqual(report['micro']['fp'],0)
        self.assertEqual(report['micro']['support'],1)
        self.assertEqual(report['micro']['tp'],1)

    def test_dates_normalize_but_invoice_leading_zeros_remain_significant(self):
        from scripts.evaluate import normalize
        self.assertEqual(normalize('01/10/2024','invoice_date'),normalize('2024-10-01','invoice_date'))
        self.assertNotEqual(normalize('00123','invoice_number'),normalize('123','invoice_number'))

if __name__=='__main__':
    unittest.main()
