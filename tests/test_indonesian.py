import unittest
from unittest.mock import patch
from PIL import Image
from backend.indonesian import fields,number,validate,line_items,detect
from backend.receipt_ocr import recognize
from backend.ocr_engine import Token


def tokens(lines):
    return [{'text':word,'conf':95,'box':[x*120,y*40,x*120+100,y*40+25],'norm_box':[0,0,100,100]}
            for y,line in enumerate(lines) for x,word in enumerate(line.split())]

class IndonesianTests(unittest.TestCase):
    def test_idr_and_original_values_are_preserved(self):
        source=tokens(['Subtotal 100.000','Pajak 10% 10.000','Service 5.000','Total 115.000','Tunai 150.000','Kembalian 35.000'])
        with patch('backend.receipt_classifier.predict',return_value=(None,0)):
            result=fields(source,{'total_amount':{},'gstin':{}})
        self.assertEqual(result['total_amount']['value'],'115000')
        self.assertEqual(result['total_amount']['source_text'],'115.000')
        self.assertEqual(result['tax_amount']['value'],'10000')
        self.assertEqual(result['tax_amount']['label_original'],'Pajak')
        self.assertEqual(result['tax_amount']['label_en'],'Tax')
        self.assertFalse(result['gstin']['applicable'])
        self.assertEqual(validate(result,[])['status'],'ok')

    def test_spaced_separator_and_percentage_only(self):
        with patch('backend.receipt_classifier.predict',return_value=(None,0)):
            result=fields(tokens(['Total 28 ,000','Pajak 10 %']),{'total_amount':{},'tax_amount':{}})
        self.assertEqual(result['total_amount']['value'],'28000')
        self.assertIsNone(result['tax_amount']['value'])
        self.assertEqual(validate(result,[])['status'],'insufficient_data')

    def test_does_not_fabricate_missing_values_or_translate_names(self):
        with patch('backend.receipt_classifier.predict',return_value=(None,0)):
            result=fields(tokens(['Nasi Goreng 20.000']),{'total_amount':{},'vendor_name':{}})
        self.assertIsNone(result['vendor_name']['value'])
        self.assertEqual(validate(result,[])['status'],'review_needed')
        items=line_items(tokens(['2 Nasi Goreng 40.000','Total 40.000']))
        self.assertEqual(items[0]['description'],'Nasi Goreng')
        self.assertEqual(items[0]['amount'],40000)

    def test_currency_detection_and_decimal_normalization(self):
        self.assertTrue(detect('Tunai Rp 100.000'))
        self.assertFalse(detect('Invoice Subtotal Rs.100 Total Rs.118'))
        self.assertEqual(str(number('Rp 1.591.600')),'1591600')
        self.assertEqual(str(number('1.000,50')),'1000.50')

    def test_ocr_keeps_preview_and_boxes_from_one_chosen_pass(self):
        def ocr(image,psm):
            count=5 if psm==6 else 1
            return [Token('word',[0,0,10,10],[0,0,100,100],95)]*count
        image,read,diagnostics=recognize(Image.new('RGB',(100,200)),ocr,lambda image:image)
        self.assertEqual(len(read),5)
        self.assertEqual(diagnostics['selected']['psm'],6)
        self.assertEqual(len(diagnostics['passes']),4)

    def test_model_fallback_requires_visible_amount_and_is_reviewed(self):
        with patch('backend.receipt_classifier.predict',return_value=('total_amount',.99)):
            result=fields(tokens(['JUMLH 60.000']),{'total_amount':{}})
        self.assertEqual(result['total_amount']['value'],'60000')
        self.assertEqual(result['total_amount']['source'],'trained_indonesian_receipt_line')
        self.assertTrue(result['total_amount']['review_required'])
        with patch('backend.receipt_classifier.predict',return_value=('total_amount',.99)):
            result=fields(tokens(['JUMLH missing']),{'total_amount':{}})
        self.assertIsNone(result['total_amount']['value'])

    def test_perspective_adjusted_rows_keep_source_boxes(self):
        from backend.layout_extractor import group_rows
        data=[{'text':'PB1','box':[100,960,190,1014],'row_y':1000,'conf':95},
              {'text':'52,815','box':[526,924,664,988],'row_y':1002,'conf':95},
              {'text':'SVC CHRG','box':[100,1004,311,1066],'row_y':1050,'conf':95},
              {'text':'25,150','box':[528,973,664,1035],'row_y':1052,'conf':95}]
        grouped=group_rows(data)
        self.assertEqual(len(grouped),2)
        with patch('backend.receipt_classifier.predict',return_value=(None,0)):
            result=fields(data,{'tax_amount':{}})
        self.assertEqual(result['tax_amount']['value'],'52815')
        self.assertEqual(result['service_charge']['value'],'25150')
        self.assertEqual(data[1]['box'],[526,924,664,988])

    def test_long_receipt_tiles_keep_global_boxes_without_duplicate_rows(self):
        from backend.neural_ocr import recognize as neural
        first=Token('TOTAL 1,000',[100,1650,200,1680],[0,0,1,1],95);first.row_y=1665
        second=Token('TOTAL 1.000',[100,50,200,80],[0,0,1,1],95);second.row_y=65
        with patch('backend.neural_ocr._single',side_effect=[[first],[second],[]]):
            observed=neural(Image.new('RGB',(300,3300)))
        self.assertEqual(len(observed),1)
        self.assertEqual(observed[0].box,[100,1650,200,1680])
        self.assertEqual(observed[0].norm_box[1],500)
