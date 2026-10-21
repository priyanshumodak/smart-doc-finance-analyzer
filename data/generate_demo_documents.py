"""Create portable demonstration documents for each supported document family."""
import sys
from pathlib import Path
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data.build_training_dataset import font

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'sample_docs'

def page(title,lines):
    image=Image.new('RGB',(1000,1400),'white')
    draw=ImageDraw.Draw(image)
    draw.text((40,40),title,font=font(32,True),fill='black')
    for index,line in enumerate(lines):
        draw.text((40,110+index*40),line,font=font(22),fill='black')
    draw.text((40,1330),'SYNTHETIC DEMO DOCUMENT - NOT REAL FINANCIAL DATA',font=font(18),fill='gray')
    return image

def main():
    OUT.mkdir(exist_ok=True)
    with Image.open(ROOT/'data/training_indian_invoices/images/invoice_00001.png') as source:
        invoice=source.convert('RGB')
    invoice.save(OUT/'demo_invoice.png')
    invoice.save(OUT/'demo_invoice.pdf','PDF',resolution=150)
    receipt=page('RECEIPT',['Seller: Sample Stationery Store','Invoice No: RCPT-001','Date: 01/10/2026',
                            'Bill To: Example Customer','','Item                         Qty     Rate        Amount',
                            'Notebook                       2      50.00       100.00','',
                            'Subtotal: 100.00','Total GST: 18.00','Grand Total: 118.00'])
    receipt.save(OUT/'demo_receipt.png')
    statement=page('BANK STATEMENT',['Sample Bank - fictional account XXXX1234','Period: 01/10/2026 - 03/10/2026'])
    draw=ImageDraw.Draw(statement)
    columns=[40,230,560,690,830]
    rows=[['Date','Description','Debit','Credit','Balance'],['01/10/2026','Opening','','','1000.00'],
          ['02/10/2026','Office supplies','200.00','','800.00'],['03/10/2026','Customer payment','','500.00','1300.00']]
    for index,row in enumerate(rows):
        for x,value in zip(columns,row):
            draw.text((x,300+index*45),value,font=font(19),fill='black')
    statement.save(OUT/'demo_bank_statement.png')
    report=page('FINANCIAL REPORT',['Fictional company - quarter ended 30/09/2026',
                                     'All values in INR. Current quarter / Previous quarter','',
                                     'Revenue                 100000.00     90000.00',
                                     'Expenses                 60000.00     55000.00',
                                     'Profit                   40000.00     35000.00',
                                     'Assets                  250000.00    230000.00',
                                     'Liabilities              50000.00     45000.00'])
    report.save(OUT/'demo_financial_report.pdf','PDF',resolution=150)
    invoice.save(OUT/'demo_multipage.pdf','PDF',save_all=True,append_images=[receipt],resolution=150)
    invoice.save(OUT/'demo_multipage.tiff',save_all=True,append_images=[receipt])
    print('Created invoice, receipt, statement, report, multipage PDF and TIFF examples in',OUT,flush=True)

if __name__=='__main__':
    main()
