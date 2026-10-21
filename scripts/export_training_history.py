"""Export available saved/observed training logs and standalone vector charts."""
import csv
import json
import math
from pathlib import Path
from reportlab.graphics.shapes import Drawing,Line,String,Circle
from reportlab.graphics import renderPDF,renderSVG
from reportlab.lib import colors
ROOT=Path(__file__).resolve().parents[1]

def export():
    sources=[]
    for path in (ROOT/'models/layoutlmv3-gpu-v2').glob('checkpoint-*/trainer_state.json'):
        state=json.loads(path.read_text(encoding='utf-8-sig'));sources.extend({**row,'log_source':'saved_checkpoint'} for row in state.get('log_history',[]))
    observed=ROOT/'reports/observed_training_progress.json'
    if observed.exists():sources.extend({**row,'log_source':'observed_process_output'} for row in json.loads(observed.read_text(encoding='utf-8-sig')))
    indexed={}
    for row in sources:
        kind='validation' if 'eval_f1' in row else 'training' if 'loss' in row else 'other'
        if 'epoch' in row:indexed[(float(row['epoch']),kind)]={**row,'kind':kind}
    rows=[row for _,row in sorted(indexed.items())]
    output=ROOT/'reports';output.mkdir(exist_ok=True)
    names=['epoch','step','kind','loss','eval_loss','eval_precision','eval_recall','eval_f1','learning_rate','grad_norm','log_source']
    with (output/'gpu_training_history.csv').open('w',newline='',encoding='utf-8') as file:
        writer=csv.DictWriter(file,fieldnames=names,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    train=[r for r in rows if r.get('loss',0)>0]
    valid=[r for r in rows if r.get('eval_f1') is not None]
    if train:
        draw=Drawing(680,255);navy=colors.HexColor('#143552');blue=colors.HexColor('#26789e')
        draw.add(String(38,232,'Recorded training progress',fontName='Helvetica-Bold',fontSize=15,fillColor=navy))
        maxepoch=max(r['epoch'] for r in rows);maxepoch=max(1,maxepoch)
        def axes(x,title,ylabels):
            draw.add(String(x,207,title,fontName='Helvetica-Bold',fontSize=10))
            draw.add(Line(x,43,x,192,strokeColor=navy));draw.add(Line(x,43,x+265,43,strokeColor=navy))
            for number,label in enumerate(ylabels):
                yy=43+number*149/(len(ylabels)-1);draw.add(String(x-7,yy-3,label,textAnchor='end',fontSize=8));draw.add(Line(x,yy,x+265,yy,strokeColor=colors.HexColor('#e2e8f0')))
            for epoch in range(math.ceil(maxepoch)+1):
                if epoch>maxepoch:continue
                xx=x+265*epoch/maxepoch;draw.add(String(xx,29,str(epoch),textAnchor='middle',fontSize=8))
            draw.add(String(x+132,13,'Completed epoch (recorded logs)',textAnchor='middle',fontSize=8))
        low=math.floor(math.log10(min(r['loss'] for r in train)));high=math.ceil(math.log10(max(r['loss'] for r in train)));high=max(low+1,high)
        axes(55,'Training loss (log scale)',[f'1e{e}' for e in range(low,high+1)])
        previous=None
        for row in train:
            point=(55+265*row['epoch']/maxepoch,43+149*(math.log10(row['loss'])-low)/(high-low))
            if previous:draw.add(Line(*previous,*point,strokeColor=blue,strokeWidth=1.3))
            previous=point
        axes(390,'Validation entity F1',[str(v/4) for v in range(5)])
        previous=None
        for row in valid:
            point=(390+265*row['epoch']/maxepoch,43+149*row['eval_f1'])
            if previous:draw.add(Line(*previous,*point,strokeColor=blue,strokeWidth=1.5))
            draw.add(Circle(*point,3,fillColor=blue,strokeColor=blue));previous=point
        renderPDF.drawToFile(draw,str(output/'gpu_training_curve.pdf'))
        renderSVG.drawToFile(draw,str(output/'gpu_training_curve.svg'))
    summary={'records':len(rows),'training_loss_records':len(train),'validation_records':len(valid),'scope':'Available saved trainer logs plus captured process updates; missing log entries are not reconstructed or invented.'}
    (output/'gpu_training_history_manifest.json').write_text(json.dumps(summary,indent=2))
    return summary

if __name__=='__main__':print(json.dumps(export(),indent=2))
