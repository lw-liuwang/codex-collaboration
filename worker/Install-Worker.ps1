#Requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('A','B')][string]$Actor = 'B',
    [string]$WorkerRoot,
    [switch]$ReadOnly,
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$pythonCommand = (Get-Command python -ErrorAction Stop).Source
$python = (& $pythonCommand -c 'import sys; print(sys.executable)').Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $python)) { throw 'A working Python 3 interpreter is required.' }
$pythonw = Join-Path (Split-Path $python -Parent) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw 'pythonw.exe is required to run without a console window.' }
$script = Join-Path $PSScriptRoot 'collab_worker.py'
if (-not $WorkerRoot) { $WorkerRoot = Join-Path (Split-Path $PSScriptRoot -Parent) ".local/installed-worker-$Actor" }
$WorkerRoot = [IO.Path]::GetFullPath($WorkerRoot)
$configPath = Join-Path $WorkerRoot 'config.json'
$taskName = "GitHubCollabWorker-$Actor"
$account = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$arguments = "-X utf8 `"$script`" once --config `"$configPath`""
if (-not $ReadOnly) { $arguments += ' --apply' }
$action = New-ScheduledTaskAction -Execute $pythonw -Argument $arguments -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(30) -RepetitionInterval (New-TimeSpan -Minutes 30)
$logon = New-ScheduledTaskTrigger -AtLogOn -User $account
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 25) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger @($trigger,$logon) -Settings $settings -Principal $principal `
    -Description 'Every 30 minutes: execute structured GitHub jobs with local gh. No Codex or model.'
if ($PlanOnly) {
    [pscustomobject]@{ TaskName=$taskName; Account=$account; Executable=$pythonw; Arguments=$arguments; Interval=$trigger.Repetition.Interval; Duration=$trigger.Repetition.Duration; Config=$configPath; MultipleInstances=$settings.MultipleInstances; ExecutionTimeLimit=$settings.ExecutionTimeLimit }
    return
}
New-Item -ItemType Directory -Path $WorkerRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $configPath)) {
    $config = Get-Content -LiteralPath (Join-Path $PSScriptRoot "config.$Actor.json") -Raw | ConvertFrom-Json
    $config.state_dir = '.'
    [IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
}
$expectedActor = if ($Actor -eq 'B') { 'ZicongHe2002' } else { 'lw-liuwang' }
$installedConfig = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
if ($installedConfig.actor -ne $expectedActor) { throw 'Existing config actor does not match the requested task. No task was installed.' }
& $python -X utf8 $script doctor --config $configPath
if ($LASTEXITCODE -ne 0) { throw 'Identity or repository check failed. No scheduled task was installed.' }
# Reinstallation preserves the database, configuration, and PAUSE marker.
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $WorkerRoot 'PAUSE'))) { Start-ScheduledTask -TaskName $taskName }
Write-Output "Installed $taskName. Poll interval: 30 minutes. State: $WorkerRoot"
Write-Output 'This task runs as the logged-in Windows user. Keep the checkout and Python path available.'
