"""Verify native multipage extraction and previews through the actual running API."""
import json
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'sample_docs/demo_continued_invoice.pdf'
    response=requests.post('http://127.0.0.1:8000/extract',files={'file':(path.name,path.read_bytes(),'application/pdf')},timeout=180)
    response.raise_for_status()
    result=response.json()
    preview=requests.get(f"http://127.0.0.1:8000/documents/{result['id']}/pages/1/preview",timeout=30)
    preview.raise_for_status()
    summary={'document_id':result['id'],'sources':[page['text_source'] for page in result['pages']],
             'documents':result['document_summary']['document_count'],'status':result['status'],
             'merged_rows':len(result['document_summary']['documents'][0]['line_items']),
             'preview_bytes':len(preview.content),'seconds':result['processing_seconds']}
    (ROOT/'reports/live_upgrade_verification.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    assert summary['sources']==['pdf_text','pdf_text']
    assert summary['documents']==1 and summary['merged_rows']==2
    assert summary['status']=='ok' and preview.content.startswith(b'\x89PNG')
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    main()
