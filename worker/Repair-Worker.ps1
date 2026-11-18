#Requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('A','B')][string]$Actor = 'B',
    [ValidateRange(1,2147483647)][int]$QueueIssue = 135,
    [string]$WorkerRoot,
    [switch]$ReadOnly
)
$ErrorActionPreference = 'Stop'
if (-not $WorkerRoot) { $WorkerRoot = Join-Path (Split-Path $PSScriptRoot -Parent) ".local/installed-worker-$Actor" }
$WorkerRoot = [IO.Path]::GetFullPath($WorkerRoot)
$configPath = Join-Path $WorkerRoot 'config.json'
if (-not (Test-Path -LiteralPath $configPath)) { throw 'Installed worker config not found. Run this from the installed checkout.' }
$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$expectedActor = if ($Actor -eq 'B') { 'ZicongHe2002' } else { 'lw-liuwang' }
if ($config.actor -ne $expectedActor) { throw 'Config actor does not match. No recovery was attempted.' }
$python = (Get-Command python -ErrorAction Stop).Source
$workerScript = Join-Path $PSScriptRoot 'collab_worker.py'
$workerArgs = @('-X','utf8',$workerScript,'recover-comment','--config',$configPath,'--number',"$QueueIssue")
if (-not $ReadOnly) { $workerArgs += '--apply' }
& $python @workerArgs
if ($LASTEXITCODE -ne 0) { throw "Recovery did not complete (exit $LASTEXITCODE). See the HTTP status above and worker.log. The original schedule is unchanged." }
if ($ReadOnly) { Write-Output 'Read-only checks finished. No recovery write was sent.' }
else { Write-Output 'Target comment task completed and read back. The original 30-minute schedule is unchanged.' }
