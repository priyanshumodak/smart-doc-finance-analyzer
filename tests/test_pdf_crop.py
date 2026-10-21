import io
import unittest
import pypdfium2 as pdfium
from reportlab.pdfgen import canvas
from backend.pdf_text import load_document

class CroppedPdfTests(unittest.TestCase):
    def test_visible_crop_excludes_hidden_words_and_shifts_evidence(self):
        source=io.BytesIO()
        page=canvas.Canvas(source,pagesize=(595,842))
        page.drawString(15,790,'HIDDEN')
        for i,line in enumerate(['Visible Supplies Ltd','TAX INVOICE','Invoice No: CROP-001','Invoice Date: 01/10/2026','Subtotal: 100.00','Tax Amount: 18.00','Grand Total: 118.00']):
            page.drawString(150,760-i*25,line)
        page.save()
        document=pdfium.PdfDocument(source.getvalue())
        document[0].set_cropbox(100,100,595,842)
        cropped=io.BytesIO();document.save(cropped)
        packet=load_document(cropped.getvalue(),'crop.pdf')[0]
        self.assertEqual(packet['text_source'],'pdf_text')
        self.assertNotIn('HIDDEN',[t['text'] for t in packet['tokens']])
        visible=next(t for t in packet['tokens'] if t['text']=='Visible')
        self.assertAlmostEqual(visible['norm_box'][0],round(50*1000/495),delta=1)
        self.assertAlmostEqual(visible['box'][0],100,delta=2)
        # Evidence rectangle must contain ink on the actual rendered crop.
        import numpy as np
        pixels=np.asarray(packet['image'].crop(visible['box']).convert('L'))
        self.assertLess(pixels.min(),100)

if __name__=='__main__':unittest.main()
