"""Interactive document review dashboard."""
import io
import json
import os
import requests
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

BACKEND = os.getenv('BACKEND_URL','http://localhost:8000').rstrip('/')
st.set_page_config(page_title='Finance Document Studio',page_icon='📄',layout='wide')
st.title('Finance Document Studio')
st.caption('Upload financial scans, inspect extraction evidence, correct fields and reconcile amounts.')

def api(method,path,**kwargs):
    response = requests.request(method,BACKEND+path,timeout=kwargs.pop('timeout',300),**kwargs)
    if not response.ok:
        try:
            message = response.json().get('detail',response.text)
        except ValueError:
            message = response.text
        raise RuntimeError(f'{response.status_code}: {message}')
    return response

with st.sidebar:
    st.header('Document workspace')
    try:
        health = api('GET','/health',timeout=5).json()
        if health['ocr_available']:
            st.success('OCR ready')
        else:
            st.warning('OCR requires configuration')
        if health.get('token_model_configured'):
            st.caption('Model: trained LayoutLMv3 with OCR fallback')
        else:
            st.caption('Mode: '+health['extraction_mode'])
    except requests.RequestException:
        st.warning('Backend is unavailable')
    except RuntimeError as exc:
        st.warning(str(exc))
    threshold = st.slider('Highlight confidence below',0.0,1.0,0.6,0.05)
    query = st.text_input('Search saved filenames')
    try:
        saved = api('GET','/documents',params={'q':query},timeout=10).json()['documents']
        selected = st.selectbox('Saved documents',['']+[d['id'] for d in saved],
                                format_func=lambda key: next((d['filename']+' · '+d['status'] for d in saved if d['id']==key),'Select document'))
        if st.button('Open saved document',disabled=not selected):
            st.session_state.result = api('GET',f'/documents/{selected}').json()
            st.session_state.pop('preview',None)
    except (requests.RequestException,RuntimeError) as exc:
        st.caption(f'History unavailable: {exc}')
    st.caption('Team: Priyanshu Modak · Vishesh Dokania · Parth Zanwar')

uploads = st.file_uploader('Upload PDF, image or multipage TIFF',type=['pdf','png','jpg','jpeg','tif','tiff'],accept_multiple_files=True)
if st.button('Analyze documents',type='primary',disabled=not uploads):
    results = []
    progress = st.progress(0)
    for i,upload in enumerate(uploads):
        with st.spinner(f'Analyzing {upload.name}…'):
            try:
                result = api('POST','/extract',files={'file':(upload.name,upload.getvalue(),upload.type)}).json()
                results.append(result)
                st.session_state.result = result
                st.session_state.preview = (upload.name,upload.getvalue())
            except (requests.RequestException,RuntimeError,ValueError) as exc:
                st.error(f'{upload.name}: {exc}')
        progress.progress((i+1)/len(uploads))
    if results:
        st.session_state.batch = results

batch = st.session_state.get('batch',[])
if len(batch)>1:
    st.dataframe(pd.DataFrame([{'filename':r['filename'],'status':r['status'],'pages':r['num_pages']} for r in batch]),hide_index=True)
    chosen = st.selectbox('Batch document',range(len(batch)),format_func=lambda i: batch[i]['filename'])
    if st.button('Review selected document'):
        st.session_state.result = api('GET',f"/documents/{batch[chosen]['id']}").json()
        st.session_state.pop('preview',None)

result = st.session_state.get('result')
if not result:
    st.info('Upload a document or open one from history to begin.')
    st.stop()

st.subheader(result['filename'])
summary=result.get('document_summary')
if summary:
    with st.expander(f"Combined results: {summary['document_count']} document(s)",expanded=result['num_pages']>1):
        st.caption(summary['grouping_policy'])
        for document in summary['documents']:
            st.markdown(f"**Document {document['document']} · pages {', '.join(map(str,document['pages']))} · {document['status']}**")
            st.dataframe(pd.DataFrame([{'field':name,'value':data.get('value'),'source_page':data.get('page')}
                                       for name,data in document['fields'].items() if data.get('value') is not None]),hide_index=True,use_container_width=True)
            if document['line_items']:
                st.dataframe(pd.DataFrame(document['line_items']),hide_index=True,use_container_width=True)
            for issue in document['validation'].get('issues',[]):
                st.warning(issue)
a,b,c = st.columns(3)
a.metric('Pages',result['num_pages'])
b.metric('Review status',result['status'].replace('_',' ').title())
c.metric('Processing time',f"{result.get('processing_seconds',0):.1f}s")
page_index = st.selectbox('Page',range(result['num_pages']),format_func=lambda i:f'Page {i+1}')
page = result['pages'][page_index]
for warning in page.get('warnings',[]):
    st.warning(warning)
left,right = st.columns([1,1.3])
with left:
    st.markdown('**Document evidence**')
    selected_field=st.selectbox('Highlight a field',['']+[name for name,data in page['fields'].items() if data.get('value')],
                                format_func=lambda name:name.replace('_',' ').title() if name else 'Choose a field',
                                key=f"field-highlight-{result['id']}-{page_index}")
    show_layout=st.checkbox('Show all word boxes',key=f"layout-{result['id']}-{page_index}")
    if page.get('preview_available'):
        try:
            @st.cache_data(ttl=600,show_spinner=False)
            def load_preview(document_id,number):
                return api('GET',f'/documents/{document_id}/pages/{number}/preview',timeout=30).content
            image=Image.open(io.BytesIO(load_preview(result['id'],page_index+1))).convert('RGB')
            draw=ImageDraw.Draw(image)
            if show_layout:
                for token in page.get('ocr_tokens',[]):
                    confidence=token.get('conf')
                    draw.rectangle(token['box'],outline='red' if confidence is not None and confidence<60 else 'steelblue',width=2)
            if selected_field:
                boxes=page['fields'][selected_field].get('boxes',[])
                for box in boxes:
                    draw.rectangle(box,outline='#ff9800',width=5)
                if not boxes:
                    st.info('No source words align with this value. Check the original extraction or review the correction.')
            st.image(image,caption='Processed source page. Orange highlights show the selected field.',use_column_width=True)
        except (requests.RequestException,RuntimeError,OSError,ValueError) as exc:
            st.warning(f'Page preview unavailable: {exc}')
    else:
        st.info('Reprocess this document to enable source previews and field highlights.')
    st.caption('Text source: '+('embedded PDF text' if page.get('text_source')=='pdf_text' else 'OCR'))
    st.text_area('OCR text',page.get('ocr_text',''),height=320,key=f"ocr-{result['id']}-{page_index}")
    st.caption('Detected type: '+page.get('document_type','unknown'))
with right:
    fields = [{'field':key,'value':data.get('value') or '', 'confidence':data.get('confidence'),
               'source':data.get('source','unknown')} for key,data in page['fields'].items()
              if page.get('document_type') not in ('bank_statement','financial_report') or data.get('value') is not None]
    low = sum(row['value']!='' and row['confidence'] is not None and row['confidence']<threshold for row in fields)
    st.caption(f'{low} populated fields below the confidence threshold. Rule scores are heuristic, not calibrated probabilities.')
    with st.form(f"review-{result['id']}-{page_index}-{result.get('reviewed_at','initial')}"):
        edited = st.data_editor(pd.DataFrame(fields,columns=['field','value','confidence','source']),disabled=['field','confidence','source'],hide_index=True,use_container_width=True)
        items = pd.DataFrame(page['line_items'])
        columns = ['description','qty','rate','amount']+[name for name in ('hsn','discount','tax') if name in items.columns]
        if items.empty:
            items = pd.DataFrame(columns=columns)
        edited_items = st.data_editor(items.reindex(columns=columns),num_rows='dynamic',hide_index=True,use_container_width=True)
        edited_transactions=None
        if page.get('document_type')=='bank_statement':
            st.markdown('**Review transactions**')
            transaction_columns=['date','description','debit','credit','balance']
            edited_transactions=st.data_editor(pd.DataFrame(page.get('transactions',[])).reindex(columns=transaction_columns),
                                               num_rows='dynamic',hide_index=True,use_container_width=True)
        submitted = st.form_submit_button('Save corrections and revalidate')
    if submitted:
        changes = {row['field']:(None if pd.isna(row['value']) else str(row['value']).strip() or None) for row in edited.to_dict('records')
                   if (None if pd.isna(row['value']) else str(row['value']).strip() or None) != page['fields'][row['field']].get('value')}
        clean_items = json.loads(edited_items.to_json(orient='records'))
        payload={'page':page_index+1,'fields':changes,'line_items':clean_items}
        if edited_transactions is not None:
            payload['transactions']=json.loads(edited_transactions.to_json(orient='records'))
        try:
            st.session_state.result = api('PATCH',f"/documents/{result['id']}",json=payload).json()
            st.rerun()
        except (requests.RequestException,RuntimeError) as exc:
            st.error(str(exc))
    for title,key in [('Transactions','transactions'),('Balance checks','balance_checks'),('Financial metrics','financial_metrics'),('Spatial field evidence','relations')]:
        if page.get(key):
            with st.expander(title):
                st.dataframe(pd.DataFrame(page[key]),hide_index=True,use_container_width=True)
    validation = page['validation']
    if validation['status']=='ok':
        st.success('All implemented checks passed')
    elif validation['status']=='insufficient_data':
        st.info('Insufficient evidence to complete reconciliation')
    else:
        st.warning('Review required')
    for reason in page.get('review_reasons',[]):
        st.caption(reason['code'].replace('_',' ').title()+': '+reason['message'])
    for issue in validation.get('issues',[]):
        st.write('• '+issue)
    st.dataframe(pd.DataFrame(validation['amount_reconciliation']['checks']),hide_index=True,use_container_width=True)
    with st.expander('Full validation and extraction provenance'):
        st.json({'validation':validation,'fields':page['fields'],'extraction_diagnostics':page.get('extraction_diagnostics',{})})

if page.get('document_type') in ('invoice','receipt','unknown'):
    with st.expander('Save a reviewed training example'):
        st.caption('Only explicitly reviewed pages are exported. Unmatched corrected text remains pending token annotation; reserved evaluation invoices are blocked.')
        confirmed=st.checkbox('I checked this page against its source',key=f"training-confirm-{result['id']}-{page_index}")
        if st.button('Approve page for training',disabled=not confirmed or not page.get('reviewed_at')):
            try:
                approval=api('POST',f"/documents/{result['id']}/pages/{page_index+1}/approve-training").json()
                if approval['ready_for_training']:
                    st.success('Approved and aligned for training export.')
                else:
                    st.warning('Saved for review; these corrected fields need token annotation: '+', '.join(approval['unmatched_fields']))
            except (requests.RequestException,RuntimeError) as exc:
                st.error(str(exc))
st.download_button('Download JSON',json.dumps(result,ensure_ascii=False,indent=2),file_name='extracted.json',mime='application/json')
if st.button('Prepare Excel download'):
    try:
        data = api('GET',f"/documents/{result['id']}/excel").content
        st.session_state.excel = (result['id'],result.get('reviewed_at'),data)
    except (requests.RequestException,RuntimeError) as exc:
        st.error(str(exc))
excel = st.session_state.get('excel')
if excel and excel[:2]==(result['id'],result.get('reviewed_at')):
    st.download_button('Download Excel',excel[2],file_name='extracted.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
