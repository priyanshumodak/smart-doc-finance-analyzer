$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$statePath=Join-Path $projectRoot 'run\services.json'
if (-not (Test-Path -LiteralPath $statePath)) { Write-Output 'No saved service processes.'; exit }
$state=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
function Stop-ServiceTree([int]$ProcessId) {
    $children=Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) { Stop-ServiceTree -ProcessId $child.ProcessId }
    Stop-Process -Id $ProcessId -ErrorAction SilentlyContinue
}
foreach ($service in @('backend','frontend')) {
    $processId=$state.$service
    $process=Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
    if ($process -and ($process.ExecutablePath -like "$projectRoot\*" -or $process.CommandLine -like "*$projectRoot*")) {
        Stop-ServiceTree -ProcessId $processId
        Write-Output "Stopped $service process tree ($processId)"
    } elseif ($process) { Write-Warning "PID $processId belongs to another application; left running." }
}
