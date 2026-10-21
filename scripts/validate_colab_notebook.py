"""Normalize the generated Colab notebook to ordinary Python cells and check syntax."""
import json
from pathlib import Path
path=Path('notebooks/train_on_colab.ipynb')
notebook=json.loads(path.read_text())
for cell in notebook['cells']:
    if cell['cell_type']!='code':
        continue
    lines=[]
    needs_subprocess=False
    for line in cell['source']:
        if line.lstrip().startswith('!'):
            indent=line[:len(line)-len(line.lstrip())]
            command=line.lstrip()[1:].rstrip()
            lines.append(indent+'subprocess.run('+repr(command)+',shell=True,check=True)\n')
            needs_subprocess=True
        else:
            lines.append(line)
    if needs_subprocess:
        lines.insert(0,'import subprocess\n')
    source=''.join(lines)
    compile(source,'colab-cell','exec')
    cell['source']=source.splitlines(True)
path.write_text(json.dumps(notebook,indent=2),encoding='utf-8')
print('All Colab code cells passed Python syntax validation')
