"""Verify the actual running backend/dashboard and a trained-model upload/export."""
import json
import time
from pathlib import Path
from collections import Counter
import requests

ROOT=Path(__file__).resolve().parents[1]

def main():
    health=None
    for attempt in range(30):
        try:
            response=requests.get('http://127.0.0.1:8000/health',timeout=5)
            response.raise_for_status()
            health=response.json()
            break
        except requests.RequestException:
            time.sleep(1)
    if health is None:
        raise RuntimeError('Backend did not become ready')
    requests.get('http://127.0.0.1:8501/_stcore/health',timeout=10).raise_for_status()
    path=ROOT/'sample_docs/demo_invoice.png'
    response=requests.post('http://127.0.0.1:8000/extract',files={'file':(path.name,path.read_bytes(),'image/png')},timeout=180)
    response.raise_for_status()
    result=response.json()
    page=result['pages'][0]
    counts=dict(Counter(value.get('source') for value in page['fields'].values()))
    assert page['ocr_token_count']>10
    assert len(page['line_items'])>=2
    assert not any('Token model unavailable' in warning for warning in page.get('warnings',[])),page.get('warnings')
    if health['token_model_configured']:
        assert page.get('extraction_diagnostics',{}).get('token_model',{}).get('status')=='executed','Token model did not execute successfully'
    preferred=ROOT/'run/preferred_model.json'
    if preferred.exists() and health.get('token_model_configured'):
        selected=json.loads(preferred.read_text(encoding='utf-8-sig'))['model_path']
        assert health.get('token_model_name')==Path(selected).name,'Running API uses a different checkpoint'
        assert page['extraction_diagnostics']['token_model']['model_name']==Path(selected).name
    workbook=requests.get(f"http://127.0.0.1:8000/documents/{result['id']}/excel",timeout=30)
    workbook.raise_for_status()
    assert workbook.content.startswith(b'PK')
    artifacts=ROOT/'artifacts'
    artifacts.mkdir(exist_ok=True)
    (artifacts/'DEMO_OUTPUT.xlsx').write_bytes(workbook.content)
    (artifacts/'DEMO_OUTPUT.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    summary={'health':health,'document_id':result['id'],'status':result['status'],'field_sources':counts,'extraction_diagnostics':page.get('extraction_diagnostics',{}),
             'warnings':page.get('warnings',[]),'processing_seconds':result['processing_seconds'],
             'line_items':len(page['line_items']),'xlsx_bytes':len(workbook.content),'integration_check':'passed',
             'scope':'Live upload of a generated training example verifies integration, not held-out accuracy'}
    (ROOT/'reports/live_app_verification.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (ROOT/'reports/live_extraction.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    main()
