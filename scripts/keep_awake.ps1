$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class UpgradeAwake {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern uint SetThreadExecutionState(uint flags);
}
"@
try {
    # Keep the system awake only while this project's completion job runs.
    # The display and permanent Windows power settings are unchanged.
    $result=[UpgradeAwake]::SetThreadExecutionState([uint32]2147483649)
    if ($result -eq 0) { throw 'Unable to request temporary system wakefulness' }
    while ($true) {
        $state=Get-Content run/upgrade_completion.json -Raw | ConvertFrom-Json
        if ($state.status -ne 'running') { break }
        $worker=Get-CimInstance Win32_Process -Filter "ProcessId=$($state.process_id)" -ErrorAction SilentlyContinue
        if (-not $worker -or $worker.CommandLine -notlike '*finish_upgrade.ps1*') { break }
        Start-Sleep -Seconds 30
    }
} finally { [UpgradeAwake]::SetThreadExecutionState([uint32]2147483648) | Out-Null }
