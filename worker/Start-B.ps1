#Requires -Version 5.1
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'

function Invoke-BWorkerSetup {
    param([string]$SourceRoot = (Split-Path $PSScriptRoot -Parent))
    Get-Command gh,git,python -ErrorAction Stop | Out-Null
    $login = & gh api user --jq .login
    if ($LASTEXITCODE -ne 0 -or "$login".Trim() -cne 'ZicongHe2002') {
        throw 'Use B local gh login (ZicongHe2002). No task or GitHub data was changed.'
    }

    $task = @(Get-ScheduledTask -ErrorAction Stop | Where-Object TaskName -eq 'GitHubCollabWorker-B')
    if ($task.Count -gt 1) { throw 'More than one B task was found. Keep the existing installation unchanged.' }
    $workerRoot = $null
    if ($task.Count -eq 1) {
        if ($task[0].State -eq 'Disabled') { throw 'B task is disabled. This launcher will not resume it.' }
        $actions = @($task[0].Actions)
        $pattern = '^-X utf8 "(?<script>[^"]+)" once --config "(?<config>[^"]+)" --apply$'
        if ($actions.Count -ne 1 -or $actions[0].Arguments -notmatch $pattern) {
            throw 'Existing B task has an unknown or read-only command. No schedule was replaced.'
        }
        $scriptPath = [IO.Path]::GetFullPath($Matches.script)
        $configPath = [IO.Path]::GetFullPath($Matches.config)
        if ((Split-Path $scriptPath -Leaf) -ne 'collab_worker.py' -or -not (Test-Path -LiteralPath $configPath)) {
            throw 'Existing worker script or configuration was not recognized.'
        }
        $checkout = Split-Path (Split-Path $scriptPath -Parent) -Parent
        $expectedScript = [IO.Path]::GetFullPath((Join-Path $checkout 'worker/collab_worker.py'))
        if ($scriptPath -ne $expectedScript) { throw 'Existing task does not run the shared worker path. No schedule was replaced.' }
        $workerRoot = Split-Path $configPath -Parent
        $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
        if ($config.actor -cne 'ZicongHe2002' -or $config.state_dir -ne '.') {
            throw 'Existing B config uses an unexpected identity or state directory. No data was changed.'
        }
        if (Test-Path -LiteralPath (Join-Path $workerRoot 'PAUSE')) {
            throw 'B worker is paused. The pause marker was preserved; no recovery was started.'
        }
    } else {
        # Source ZIPs have no .git. Use a stable checkout outside Downloads.
        if (Test-Path -LiteralPath (Join-Path $SourceRoot '.git')) { $checkout = $SourceRoot }
        else {
            $installRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'GitHubCollabWorker'
            $checkout = Join-Path $installRoot 'codex-collaboration'
            if (-not (Test-Path -LiteralPath $checkout)) {
                New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
                & git clone -- https://github.com/lw-liuwang/codex-collaboration.git $checkout
                if ($LASTEXITCODE -ne 0) { throw 'Clone failed. Run the same launcher again after fixing Git/network access.' }
            }
        }
    }

    Push-Location -LiteralPath $checkout
    try {
        $remote = & git remote get-url origin
        if ($LASTEXITCODE -ne 0 -or "$remote".Trim() -notmatch '^https://github\.com/lw-liuwang/codex-collaboration(?:\.git)?$') {
            throw 'The checkout origin is not the shared collaboration repository.'
        }
        $branch = & git branch --show-current
        if ($LASTEXITCODE -ne 0 -or "$branch".Trim() -ne 'main') { throw 'Checkout must be on main. Existing branches were preserved.' }
        $changes = & git status --porcelain --untracked-files=no
        if ($LASTEXITCODE -ne 0 -or $changes) { throw 'Checkout has tracked edits. Save them before running this launcher.' }
        & git pull --ff-only origin main
        if ($LASTEXITCODE -ne 0) { throw 'Fast-forward update failed. No reset, stash or schedule replacement was attempted.' }
        if ($workerRoot) {
            & (Join-Path $checkout 'worker/Repair-Worker.ps1') -Actor B -WorkerRoot $workerRoot
            Write-Output 'Existing task schedule and database were preserved.'
        } else {
            & (Join-Path $checkout 'worker/Install-Worker.ps1') -Actor B
            Write-Output 'B task installed. The first scan has been requested; check the health page for completion.'
        }
        & (Join-Path $checkout 'worker/Control-Worker.ps1') -Actor B -Action Status -WorkerRoot $workerRoot
        Write-Output 'Health: https://github.com/lw-liuwang/codex-collaboration/issues/131'
        Write-Output 'Queue:  https://github.com/lw-liuwang/codex-collaboration/issues/135'
    } finally { Pop-Location }
}

if ($MyInvocation.InvocationName -ne '.') {
    try { Invoke-BWorkerSetup }
    catch { Write-Host $_.Exception.Message -ForegroundColor Red; exit 1 }
}
