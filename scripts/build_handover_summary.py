"""Write a concise return-from-AFK handover using measured artifacts."""
import json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def read(relative):
    path=ROOT/relative
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else None

def build():
    result=read('reports/upgrade_results.json') or {}
    state=read('run/upgrade_completion.json') or {}
    model=result.get('gpu_training') or {}
    selected=read('run/preferred_model.json') or {}
    operating=read('run/preferred_mode.json') or {}
    mode=operating.get('recommended_mode','ocr')
    command=r'.\scripts\start.ps1 -Mode '+mode+(' -UseGpu' if mode=='token' else '')
    lines=['# Welcome back: project handover','',f"Updated: {datetime.now(timezone.utc).isoformat()} (UTC)",'',
        f"Completion workflow: **{state.get('status','not recorded')}**; stage: `{state.get('stage','not recorded')}`.",
        f"Final model training/evaluation: **{'complete' if result.get('gpu_training_finished') else 'pending'}**.",'',
        '## What to do first','',
        '1. Open http://127.0.0.1:8501. If Windows restarted, use the startup instructions below.',
        '2. Upload `sample_docs/demo_digital_invoice.pdf`, click Analyze documents and inspect field evidence/checks.',
        '3. Upload `demo_continued_invoice.pdf` and inspect the combined invoice and two merged rows.',
        '4. Open `artifacts/PROFESSOR_PRESENTATION.pptx` for editable slides/speaker notes, or the matching PDF.',
        '5. Read [the full demonstration guide](PROFESSOR_DEMO.md) and [start-here instructions](START_HERE.md).','',
        '## Implemented updates','',
        '- Reliable native PDF words/tables with per-page OCR fallback.',
        '- Correct visible-crop coordinates and actual source-page field highlights.',
        '- Independent model/rule candidates, validity checks, explicit conflicts and arithmetic evidence.',
        '- Wrapped invoice rows and retained HSN/discount/tax columns.',
        '- Conservative multipage grouping, combined validation and merged Excel sheets.',
        '- Editable bank transactions with recalculated balance checks.',
        '- Explicit reviewed-page approval, aligned train-only export and reserved-evaluation guards.',
        '- Isolated CUDA training/inference, preserved CPU baseline and checkpoint/device diagnostics.',
        '- 500 additional external synthetic invoices with provenance, original JSON and image hashes.',
        '- Complete handbook, editable slides, API/architecture guide, training instructions, troubleshooting and viva preparation.','',
        'Recommended mode: **'+mode+'**. This is selected on final-field validation quality; model BIO scores describe a separate task.','', '## Measured verification','']
    for suite in result.get('regression_suites') or []:
        lines.append(f"- {suite['suite']}: {suite['tests']} tests {'passed' if suite['passed'] else 'FAILED'}.")
    if result.get('gpu_training_finished'):
        lines+=['',f"New run: {model.get('completed_optimizer_steps')} optimizer updates across {model.get('completed_epochs')} completed epochs; warm-started from `{model.get('base_model')}`.",f"Selected checkpoint for optional token mode: `{selected.get('model_path','not recorded')}`.",'', '| Model | Validation F1 | Test F1 |','|---|---:|---:|']
        oldv=result.get('matched_full_baseline_validation');oldt=result.get('matched_full_baseline_test')
        if oldv and oldt:lines.append(f"| Preserved baseline, 150 examples/split | {oldv['validation_f1']:.4f} | {oldt['test_f1']:.4f} |")
        lines.append(f"| New GPU model, 150 examples/split | {result['validation']['validation_f1']:.4f} | {result['test']['test_f1']:.4f} |")
        lines+=['','These are synthetic BIO entity metrics using supplied word boxes. Final OCR/pipeline scores are separate in the upgrade report.']
    if result.get('gpu_training_finished'):
        lines+=['',f"The run completed its full budget, but validation selected the weights saved at step {model.get('selected_checkpoint_optimizer_step','see selected_checkpoint')}, epoch {model.get('selected_checkpoint_epoch','see metadata')}. Later updates were not automatically deployed merely because they were newer."]
    else:lines+=['','Training or final evaluation is still pending. Read [current status](STATUS.md); no final score is invented.']
    if operating:
        lines+=['',f"Operating-mode validation: OCR field F1 {operating['scores']['ocr']['f1']:.3f}; combined token-mode field F1 {operating['scores']['token']['f1']:.3f}, on the same {operating['validation_documents']} synthetic validation documents."]
        reserved=result.get('recommended_mode_test')
        if reserved:
            lines+=['',f"After selection, a separate reserved {reserved['documents']}-document synthetic test slice yielded field F1 {reserved['micro']['f1']:.3f} and field accuracy {reserved['micro']['accuracy']:.3f}. This is not a real-world benchmark."]
    lines+=['','## Restart on this laptop','', '```powershell',f"Set-Location -LiteralPath '{ROOT}'",command,'```','',
        'Use `scripts/stop.ps1` first if services already occupy the ports. For the optional neural-model demonstration use `scripts/start.ps1 -Mode token -UseGpu`; CPU model inference omits `-UseGpu`. Do not start duplicate training workers.','',
        '## Deliverables','',
        '- `artifacts/PROJECT_HANDBOOK.pdf`: full printable instructions and measured report.',
        '- `artifacts/PROFESSOR_PRESENTATION.pptx` and `.pdf`: presentation, with speaker notes in the editable deck.',
        '- `artifacts/finance-analyzer.zip`: source, public datasets, docs, presentation and demo outputs.',
        '- `artifacts/finance-analyzer-model.zip`: separate selected inference model with hashes, generated after successful verification.',
        '- `artifacts/DEMO_OUTPUT.json` and `.xlsx`: live generated-invoice example outputs.',
        '- `reports/UPGRADE_RESULTS.md`: exact settings, measured comparisons, scope and limitations.',
        '- `reports/gpu_training_history.csv` and `gpu_training_curve.pdf/.svg`: available actual training logs and vector charts.','',
        'The source archive excludes installed environments, model weights, saved history and private reviewed datasets. Extract the separate model archive into the project root to transfer token mode. Keep database/previews in a separate private backup if needed.','',
        '## Remaining limitations','',
        'Real Indian-invoice accuracy is not established. The external corpus is also synthetic and exposed poor OCR-only generalization on five validation images (3/20 annotated fields recovered). Read the final combined external result separately. Robust handwriting/Hindi evaluation, trained table structure and production deployment remain future work. The laptop has verified English/orientation OCR packs; Hindi training/accuracy is not claimed.','',
        'For the final successful handover read `run/upgrade-finalization.log`. Intermediate comparison/deployment attempts are retained in `run/upgrade-finish-resume.log` and `run/upgrade-finish-resume-error.log`. The earlier logs are retained in `run/upgrade-finish.log` and `run/upgrade-finish-error.log`; their encoding failure was fixed without retraining. Refresh this snapshot with `backend/venv/Scripts/python.exe scripts/build_handbook.py` after refreshing the status and upgrade report.']
    (ROOT/'docs/RETURN_FROM_AFK.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':build()
