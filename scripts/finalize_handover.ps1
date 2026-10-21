$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
function Run-Checked([string]$Script,[string[]]$Extra=@()) {
    & backend/venv/Scripts/python.exe $Script @Extra
    if ($LASTEXITCODE -ne 0) { throw "Finalization failed: $Script" }
}
try {
    if (-not (Test-Path artifacts/finance-analyzer-model.zip)) { throw 'Selected model archive is missing' }
    $health=Invoke-RestMethod http://127.0.0.1:8000/health
    $mode=Get-Content run/preferred_mode.json -Raw | ConvertFrom-Json
    if ($mode.recommended_mode -ne 'ocr' -or $health.extraction_mode -ne 'ocr') { throw 'Running mode does not match selected default' }
    Run-Checked 'scripts/build_upgrade_report.py'
    Run-Checked 'scripts/project_status.py' @('--write')
    Run-Checked 'scripts/build_handbook.py'
    Run-Checked 'scripts/package_project.py' @('--dataset')
    @{status='complete';stage='finished';finished_at=(Get-Date).ToString('o');recommended_mode='ocr';message='Training, matched evaluation, validation-based operating-mode choice, separate reserved test, 43 regressions, GPU HTTP smoke test, recommended-mode live checks, handbook, slides, demo outputs and both archives verified.'} | ConvertTo-Json | Set-Content -Encoding UTF8 run/upgrade_completion.json
    Run-Checked 'scripts/project_status.py' @('--write')
    Run-Checked 'scripts/build_handbook.py'
    Run-Checked 'scripts/package_project.py' @('--dataset')
    Write-Output 'Final deliverables and completion status refreshed successfully.'
} catch {
    @{status='failed';stage='final_documentation_and_packaging';message=$_.Exception.Message;updated_at=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -Encoding UTF8 run/upgrade_completion.json
    throw
}
