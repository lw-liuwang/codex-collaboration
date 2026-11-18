#Requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('Status','Pause','Resume','Uninstall')][string]$Action = 'Status',
    [ValidateSet('A','B')][string]$Actor = 'B',
    [string]$WorkerRoot
)
$ErrorActionPreference = 'Stop'
if (-not $WorkerRoot) { $WorkerRoot = Join-Path (Split-Path $PSScriptRoot -Parent) ".local/installed-worker-$Actor" }
$WorkerRoot = [IO.Path]::GetFullPath($WorkerRoot)
$taskName = "GitHubCollabWorker-$Actor"
$pause = Join-Path $WorkerRoot 'PAUSE'
switch ($Action) {
    'Pause' {
        New-Item -ItemType Directory -Path $WorkerRoot -Force | Out-Null
        [IO.File]::WriteAllText($pause, 'Paused explicitly by the local operator.')
        Write-Output 'Paused. An in-flight request may finish; no subsequent write will start.'
    }
    'Resume' {
        if (Test-Path -LiteralPath $pause) { Remove-Item -LiteralPath $pause }
        Start-ScheduledTask -TaskName $taskName
    }
    'Uninstall' {
        New-Item -ItemType Directory -Path $WorkerRoot -Force | Out-Null
        [IO.File]::WriteAllText($pause, 'Uninstalled by the local operator.')
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Output 'Uninstalled. Local database, logs, and receipts were preserved.'
    }
    'Status' {
        Get-ScheduledTask -TaskName $taskName | Select-Object TaskName,State
        Get-ScheduledTaskInfo -TaskName $taskName | Select-Object LastRunTime,LastTaskResult,NextRunTime
        Write-Output "Paused: $(Test-Path -LiteralPath $pause)"
        $statusPath = Join-Path $WorkerRoot 'status.json'
        if (Test-Path -LiteralPath $statusPath) { Get-Content -LiteralPath $statusPath -Raw }
    }
}
