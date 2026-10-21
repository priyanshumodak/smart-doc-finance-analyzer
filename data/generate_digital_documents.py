"""Digital PDFs for demonstrating text extraction, highlighting and invoice continuation."""
from pathlib import Path
import sys
from reportlab.pdfgen import canvas
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.validation import gstin_check_digit
ROOT=Path(__file__).resolve().parents[1]

def create(path,pages=1):
    document=canvas.Canvas(str(path),pagesize=(595,842))
    gstin='27ABCDE1234F1Z'
    gstin+=gstin_check_digit(gstin)
    for number in range(1,pages+1):
        document.setFont('Helvetica-Bold',17)
        document.drawString(40,795,'Native Demo Supplies Ltd')
        document.setFont('Helvetica',11)
        lines=['TAX INVOICE','Invoice No: DEMO-DIGITAL-2026', 'Invoice Date: 01/10/2026',
               f'Seller GSTIN: {gstin}','Seller PAN: ABCDE1234F','Bill To: Example College',f'Page {number} of {pages}']
        for index,text in enumerate(lines):
            document.drawString(40,760-index*22,text)
        columns=[40,280,350,410,480]
        for x,name in zip(columns,['Description','HSN','Qty','Rate','Amount']):
            document.drawString(x,570,name)
        document.line(40,562,555,562)
        for x,value in zip(columns,['Office Paper','4802',str(number),'100.00',f'{number*100:.2f}']):
            document.drawString(x,540,value)
        if number==pages:
            subtotal=sum(range(1,pages+1))*100
            for index,text in enumerate([f'Subtotal: {subtotal:.2f}',f'CGST: {subtotal*.09:.2f}',f'SGST: {subtotal*.09:.2f}',
                                         'IGST: 0.00',f'Total GST: {subtotal*.18:.2f}',f'Grand Total: {subtotal*1.18:.2f}']):
                document.drawString(340,480-index*24,text)
        document.drawString(40,40,'SYNTHETIC DEMONSTRATION - NOT A REAL TAX INVOICE')
        document.showPage()
    document.save()

def main():
    output=ROOT/'sample_docs'
    create(output/'demo_digital_invoice.pdf')
    create(output/'demo_continued_invoice.pdf',2)
    print('Created native-text single-page and continued two-page invoice PDFs',flush=True)

if __name__=='__main__':
    main()
