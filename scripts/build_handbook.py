"""Build a printable handbook from maintained Markdown and measured status artifacts."""
import argparse
import re
import textwrap
from datetime import datetime,timezone
from html import escape
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Preformatted
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon
ROOT=Path(__file__).resolve().parents[1]
CHAPTERS=['RETURN_FROM_AFK.md','START_HERE.md','STATUS.md','INSTALLATION.md','USER_WALKTHROUGH.md','TRAINING_AND_DATA.md','ARCHITECTURE_AND_API.md','PROFESSOR_DEMO.md','CHANGELOG.md','REFERENCES.md']
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='ManualBody',parent=styles['BodyText'],fontSize=9.3,leading=13,spaceAfter=7))
styles.add(ParagraphStyle(name='ManualCell',parent=styles['BodyText'],fontSize=8,leading=10))
styles.add(ParagraphStyle(name='ManualCode',fontName='Courier',fontSize=7,leading=9,backColor=colors.HexColor('#f1f5f9'),borderPadding=7,spaceAfter=10))
styles.add(ParagraphStyle(name='ManualCover',parent=styles['Title'],fontSize=30,leading=36,textColor=colors.HexColor('#143552'),spaceAfter=18))
for name in ('Heading1','Heading2','Heading3'):
    styles[name].textColor=colors.HexColor('#143552')
    styles[name].spaceBefore=12

def inline(raw):
    value=escape(raw)
    value=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',lambda m:f'<link href="{m[2]}">{m[1]}</link>' if m[2].startswith(('https://','http://')) else m[1]+' ('+m[2]+')',value)
    value=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',value)
    value=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',value)
    return value

def pipeline():
    drawing=Drawing(460,135)
    labels=[('Upload','Bounds and format'),('Text + coordinates','PDF words or OCR'),('Extraction','Model and rules'),('Tables + checks','Geometry and arithmetic'),('Human review','Source evidence'),('Export','JSON and Excel')]
    for i,(title,subtitle) in enumerate(labels):
        x=(i%3)*155;y=88-(i//3)*68
        drawing.add(Rect(x,y,145,40,rx=6,ry=6,fillColor=colors.HexColor('#e8f1f7'),strokeColor=colors.HexColor('#3a6e92')))
        drawing.add(String(x+72,y+25,title,textAnchor='middle',fontName='Helvetica-Bold',fontSize=10))
        drawing.add(String(x+72,y+10,subtitle,textAnchor='middle',fontName='Helvetica',fontSize=8))
        if i%3<2:
            drawing.add(Line(x+145,y+20,x+154,y+20,strokeColor=colors.HexColor('#3a6e92')))
    return drawing

def markdown(path):
    lines=path.read_text(encoding='utf-8-sig').splitlines();out=[];index=0
    while index<len(lines):
        line=lines[index].rstrip()
        if not line:
            index+=1;continue
        if line.startswith('```'):
            language=line[3:].strip();code=[];index+=1
            while index<len(lines) and not lines[index].startswith('```'):
                code.extend(textwrap.wrap(lines[index],width=104,replace_whitespace=False,drop_whitespace=False) or [''])
                index+=1
            if language=='mermaid': out.append(pipeline())
            else: out.append(Preformatted('\n'.join(code),styles['ManualCode']))
        elif line.startswith('|'):
            rows=[]
            while index<len(lines) and lines[index].startswith('|'):
                cells=[cell.strip() for cell in lines[index].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',cell) for cell in cells): rows.append(cells)
                index+=1
            count=max(map(len,rows));weights=[max(8,min(65,max(len(r[c]) if c<len(r) else 0 for r in rows))) for c in range(count)]
            widths=[460*w/sum(weights) for w in weights]
            data=[[Paragraph(inline(cell),styles['ManualCell']) for cell in row+['']*(count-len(row))] for row in rows]
            table=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#ddeaf3')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f7f9fb')]),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#cbd5e1')),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            out+=[table,Spacer(1,10)];continue
        elif line.startswith('#'):
            level=min(3,len(line)-len(line.lstrip('#')))
            out.append(Paragraph(inline(line.lstrip('#').strip()),styles[f'Heading{level}']))
        else:
            bullet=line.startswith('- ')
            out.append(Paragraph(inline(line[2:] if bullet else line),styles['ManualBody'],bulletText='\u2022' if bullet else None))
        index+=1
    return out

def footer(canvas,doc):
    canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#64748b'))
    canvas.drawString(42,26,'Smart Document and Finance Analyzer | Local academic project')
    canvas.drawRightString(553,26,str(doc.page));canvas.restoreState()

def main():
    from build_handover_summary import build
    build()
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='artifacts/PROJECT_HANDBOOK.pdf');args=parser.parse_args()
    target=ROOT/args.out;target.parent.mkdir(exist_ok=True)
    story=[Spacer(1,65),Paragraph('Smart Document<br/>and Finance Analyzer',styles['ManualCover']),Paragraph('Setup, operation, data, training, evidence and professor demonstration',styles['Heading2']),Spacer(1,25),Paragraph('Priyanshu Modak (I080) · Vishesh Dokania (I019) · Parth Zanwar (I074)',styles['ManualBody']),Paragraph('Generated '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),styles['ManualBody']),Spacer(1,20),Paragraph('Read the Current project status chapter for actual completion. Synthetic evaluation and functional demonstrations do not establish real-document accuracy.',styles['ManualBody']),Spacer(1,15),pipeline(),PageBreak()]
    story+=[Paragraph('Reading order',styles['Heading1'])]
    for name in CHAPTERS:
        title=(ROOT/'docs'/name).read_text(encoding='utf-8-sig').splitlines()[0].lstrip('# ')
        story.append(Paragraph(inline(title),styles['ManualBody']))
    story.append(Paragraph('Measured results follow the guides. Source documentation remains available in docs/ for searching and copying commands.',styles['ManualBody']))
    for name in CHAPTERS:
        story.append(PageBreak());story.extend(markdown(ROOT/'docs'/name))
    report=ROOT/'reports/UPGRADE_RESULTS.md'
    if report.exists(): story.append(PageBreak());story.extend(markdown(report))
    document=SimpleDocTemplate(str(target),pagesize=(595,842),leftMargin=55,rightMargin=55,topMargin=45,bottomMargin=45,title='Smart Document and Finance Analyzer: Project Handbook',author='Project team')
    document.build(story,onFirstPage=footer,onLaterPages=footer)
    try:
        from build_presentation import main as build_slides
        build_slides()
    except ImportError:
        print('Install scripts/requirements_docs.txt to build editable presentation artifacts',flush=True)
    print(f'Built {target} ({target.stat().st_size:,} bytes)',flush=True)

if __name__=='__main__': main()
