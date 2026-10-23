import unittest
from scripts.download_cord import adapt
from scripts.evaluate import evaluate,normalize

class RealReceiptsTests(unittest.TestCase):
    def test_amount_keys_are_not_training_values(self):
        quad={'x1':1,'x2':10,'x3':10,'x4':1,'y1':1,'y2':1,'y3':10,'y4':10}
        raw={'gt_parse':{'total':{'total_price':'60.000'}},'valid_line':[{'category':'total.total_price','words':[
             {'text':'TOTAL','is_key':1,'quad':quad},{'text':'60.000','is_key':0,'quad':quad}]}]}
        record,annotation=adapt(raw,'receipt','images/receipt.jpg','test',(100,100))
        self.assertEqual(record['total_amount'],'60.000')
        self.assertEqual(annotation['labels'],['O','B-TOTAL_AMOUNT'])
        self.assertNotIn('gstin',record['annotated_fields'])

    def test_idr_separators_do_not_change_indian_decimal_rules(self):
        self.assertEqual(normalize('Rp 60.000','total_amount','IDR'),normalize('60000','total_amount','IDR'))
        self.assertEqual(normalize('1,591,600','total_amount','IDR'),normalize('1591600','total_amount','IDR'))
        self.assertNotEqual(normalize('60.000','total_amount'),normalize('60000','total_amount'))

    def test_unknown_invoice_fields_are_not_counted_as_errors(self):
        report=evaluate([{'image_path':'receipt.jpg','currency':'IDR','annotated_fields':['total_amount'],'total_amount':'60.000'}],
                        [{'filename':'receipt.jpg','fields':{'total_amount':{'value':'60000'},'vendor_name':{'value':'Shop'}}}])
        self.assertEqual(report['micro']['f1'],1)
        self.assertEqual(report['fields']['vendor_name']['fp'],0)
