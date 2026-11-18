#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../worker/Start-B.ps1')
function Assert($Condition, $Message) { if (-not $Condition) { throw $Message } }
$testRoot = Join-Path $PSScriptRoot "../.local/launcher test $([guid]::NewGuid().ToString('N'))"
$testRoot = [IO.Path]::GetFullPath($testRoot)
New-Item -ItemType Directory -Path (Join-Path $testRoot 'worker'),(Join-Path $testRoot 'state'),(Join-Path $testRoot '.git') -Force | Out-Null
Set-Content -LiteralPath (Join-Path $testRoot 'state/config.json') -Value '{"actor":"ZicongHe2002","state_dir":"."}'
Set-Content -LiteralPath (Join-Path $testRoot 'state/worker.sqlite3') -Value 'ledger must survive'
foreach ($name in @('Repair','Install','Control')) {
    $body = 'param($Actor,$WorkerRoot,$Action); $global:launcherCalls.Add("' + $name + ':$Actor`:$WorkerRoot`:$Action")'
    Set-Content -LiteralPath (Join-Path $testRoot "worker/$name-Worker.ps1") -Value $body
}
$global:launcherLogin = 'ZicongHe2002'
$global:launcherDirty = $false
$global:launcherCalls = [Collections.Generic.List[string]]::new()
$global:launcherTask = [pscustomobject]@{
    TaskName='GitHubCollabWorker-B'; State='Ready'; Actions=@([pscustomobject]@{
        Arguments="-X utf8 `"$testRoot/worker/collab_worker.py`" once --config `"$testRoot/state/config.json`" --apply"
    })
}
function global:gh { $global:LASTEXITCODE = 0; $global:launcherLogin }
function global:git {
    $global:LASTEXITCODE = 0
    switch ($args[0]) {
        'remote' { 'https://github.com/lw-liuwang/codex-collaboration.git' }
        'branch' { 'main' }
        'status' { if ($global:launcherDirty) { ' M worker/collab_worker.py' } }
        'pull' { $global:launcherCalls.Add('pull') }
        default { throw "Unexpected git call: $args" }
    }
}
function global:Get-ScheduledTask { param($ErrorAction); $global:launcherTask }
function Expect-Blocked($Message) {
    $blocked = $false
    try { Invoke-BWorkerSetup -SourceRoot $testRoot | Out-Null } catch { $blocked = $true }
    Assert $blocked $Message
    Assert ($global:launcherCalls.Count -eq 0) 'Blocked setup performed a side effect'
}
try {
    $ledger = Get-FileHash -LiteralPath (Join-Path $testRoot 'state/worker.sqlite3')
    $arguments = $global:launcherTask.Actions[0].Arguments
    Invoke-BWorkerSetup | Out-Null
    Assert (($global:launcherCalls -join ',') -eq "pull,Repair:B:$testRoot\state`:`,Control:B:$testRoot\state`:Status") 'Existing installation was not recovered with its original state directory'
    Assert ($global:launcherTask.Actions[0].Arguments -eq $arguments) 'Existing schedule changed'
    Assert ((Get-FileHash -LiteralPath $ledger.Path).Hash -eq $ledger.Hash) 'Existing ledger changed'
    $global:launcherCalls.Clear()
    $global:launcherLogin = 'lw-liuwang'
    Expect-Blocked 'Wrong identity was accepted'
    $global:launcherLogin = 'ZicongHe2002'
    Set-Content -LiteralPath (Join-Path $testRoot 'state/PAUSE') -Value 'paused'
    Expect-Blocked 'Pause was ignored'
    Assert (Test-Path -LiteralPath (Join-Path $testRoot 'state/PAUSE')) 'Pause marker was removed'
    Remove-Item -LiteralPath (Join-Path $testRoot 'state/PAUSE')
    $global:launcherTask.State = 'Disabled'
    Expect-Blocked 'Disabled task was resumed'
    $global:launcherTask.State = 'Ready'
    $global:launcherTask.Actions[0].Arguments = 'unknown command'
    Expect-Blocked 'Unknown task was replaced'
    $global:launcherTask.Actions[0].Arguments = $arguments
    $global:launcherDirty = $true
    Expect-Blocked 'Tracked edits were overwritten'
    $global:launcherDirty = $false
    $global:launcherTask = $null
    Invoke-BWorkerSetup -SourceRoot $testRoot | Out-Null
    Assert (($global:launcherCalls -join ',') -eq 'pull,Install:B::,Control:B::Status') 'First install did not use the installer'
    'PASS: existing paths with spaces, ledger/schedule preservation, identity, pause, disabled/unknown task, tracked edits and first installation'
} finally {
    Remove-Item Function:/gh,Function:/git,Function:/Get-ScheduledTask
    # The exact GUID test directory was created above, under this workspace.
    $expectedParent = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../.local'))
    if ((Split-Path $testRoot -Parent) -ne $expectedParent) { throw 'Unexpected test cleanup path' }
    Remove-Item -LiteralPath $testRoot -Recurse -Force
    Remove-Variable launcherLogin,launcherDirty,launcherCalls,launcherTask -Scope Global
}
