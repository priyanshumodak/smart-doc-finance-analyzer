import unittest
from pathlib import Path
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

    def test_multiple_reference_totals_are_not_silently_collapsed(self):
        record,_=adapt({'gt_parse':{'total':[{'total_price':'10.000'},{'total_price':'20.000'}]},'valid_line':[]},'receipt','receipt.png','test',(100,100))
        self.assertNotIn('total_amount',record['annotated_fields'])
        self.assertNotIn('total_amount',record)
        self.assertEqual(record['ambiguous_reference_fields']['total_amount'],['10.000','20.000'])

    def test_resume_does_not_fetch_a_complete_split_again(self):
        import tempfile,json
        from unittest.mock import patch
        from PIL import Image
        from scripts.download_cord import resumed_streaming_rows
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'images').mkdir();(root/'original_annotations').mkdir()
            for index in range(2):
                identity=f'cord_validation_{index:05d}'
                Image.new('RGB',(10,10)).save(root/'images'/f'{identity}.png')
                (root/'original_annotations'/f'{identity}.json').write_text('{}')
            with patch('scripts.download_cord.streaming_rows',side_effect=AssertionError('Completed split must stay offline')):
                self.assertEqual(len(list(resumed_streaming_rows(root,'validation',2,'revision'))),2)

    def test_pixel_audit_excludes_evaluation_and_training_duplicates(self):
        import tempfile,json
        from PIL import Image
        from scripts.audit_receipt_splits import audit
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);rows=[]
            for identity,split,color in [('train_a','train','red'),('train_b','train','blue'),('train_c','train','blue'),('valid','validation','red')]:
                Image.new('RGB',(10,10),color).save(root/f'{identity}.png')
                rows.append({'id':identity,'split':split,'image_path':f'{identity}.png'})
            (root/'ground_truth.json').write_text(json.dumps(rows))
            result=audit(root)
            self.assertEqual(result['safe_training_ids'],['train_b'])
            self.assertEqual(len(result['excluded_training_records']),2)
