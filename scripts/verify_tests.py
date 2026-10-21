"""Run backend and rendered-dashboard suites and preserve exact results for the report."""
import json
import re
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    rows=[]
    output=ROOT/'reports/test_logs'
    output.mkdir(parents=True,exist_ok=True)
    for name,python,folder in [('backend','backend/venv/Scripts/python.exe','tests'),('dashboard','frontend/venv/Scripts/python.exe','frontend/tests')]:
        process=subprocess.run([str(ROOT/python),'-m','unittest','discover','-s',folder,'-v'],cwd=ROOT,capture_output=True,text=True)
        text=process.stdout+process.stderr
        (output/f'{name}.log').write_text(text,encoding='utf-8')
        count=re.search(r'Ran (\d+) tests?',text)
        row={'suite':name,'tests':int(count[1]) if count else None,'passed':process.returncode==0}
        rows.append(row)
        print(json.dumps(row),flush=True)
    (ROOT/'reports/upgraded_tests.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    if not all(row['passed'] for row in rows):
        raise SystemExit('Regression suite failed; inspect reports/test_logs')

if __name__=='__main__':
    main()
