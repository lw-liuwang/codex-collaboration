#Requires -Version 7.0
$ErrorActionPreference = 'Stop'
Import-Module "$PSScriptRoot/../.agents/skills/github-collab/scripts/Collab.psm1" -Force
function Assert($Condition, [string]$Message) { if (-not $Condition) { throw $Message } }

$first = New-CollabPlan -Actor lw-liuwang -Date '2026-11-17'
$again = New-CollabPlan -Actor lw-liuwang -Date '2026-11-17'
Assert (($first.times -join ',') -eq ($again.times -join ',')) 'Plan must survive retries unchanged'
$plans = foreach ($actor in @('lw-liuwang','ZicongHe2002')) {
    foreach ($day in 1..28) { New-CollabPlan -Actor $actor -Date ('2026-11-{0:00}' -f $day) }
}
foreach ($plan in $plans) {
    Assert ($plan.times.Count -eq 42) 'Expected forty-two slots'
    $offset = if ($plan.actor -eq 'lw-liuwang') { 0 } else { 10 }
    $midnight = [DateTimeOffset]::Parse("$($plan.date)T00:00:00+08:00")
    for ($i=0; $i -lt $plan.times.Count; $i++) {
        $at = [DateTimeOffset]$plan.times[$i]
        Assert ($at.Hour -ge 9 -and $at.Hour -le 22) 'Wakeup outside daytime window'
        $jitter = ($at - $midnight).TotalMinutes - 540 - $i*20 - $offset
        Assert ($jitter -ge 2 -and $jitter -le 8) 'Each wakeup must stay in its own random slot'
    }
    $intervals = @()
    for ($i=1; $i -lt $plan.times.Count; $i++) {
        $gap = ([DateTimeOffset]$plan.times[$i] - [DateTimeOffset]$plan.times[$i-1]).TotalMinutes
        Assert ($gap -ge 14 -and $gap -le 26) 'Randomized gap outside intended range'
        $intervals += $gap
    }
    Assert (@($intervals | Sort-Object -Unique).Count -gt 1) 'Wakeups must not form a fixed twenty-minute grid'
}
foreach ($day in 1..28) {
    $date = '2026-11-{0:00}' -f $day
    $a = New-CollabPlan -Actor lw-liuwang -Date $date
    $b = New-CollabPlan -Actor ZicongHe2002 -Date $date
    for ($i=0; $i -lt $a.times.Count; $i++) {
        Assert (([DateTimeOffset]$b.times[$i] - [DateTimeOffset]$a.times[$i]).TotalMinutes -eq 10) 'Actors must alternate with a ten-minute offset'
    }
}

$planRoot = Join-Path $PSScriptRoot "../.local/test-plans-$([guid]::NewGuid().ToString('N'))"
try {
    $locked = Get-LockedCollabPlan -Actor lw-liuwang -Date '2026-11-17' -StateRoot $planRoot
    $planFile = Join-Path $planRoot 'lw-liuwang-2026-11-17.json'
    $before = Get-Content -LiteralPath $planFile -Raw
    (Get-Item -LiteralPath $planFile).LastWriteTimeUtc = [DateTime]'2000-01-01T00:00:00Z'
    $stamp = (Get-Item -LiteralPath $planFile).LastWriteTimeUtc
    $reloaded = Get-LockedCollabPlan -Actor lw-liuwang -Date '2026-11-17' -StateRoot $planRoot
    Assert (($locked.times -join ',') -eq ($reloaded.times -join ',')) 'Reload must keep the locked plan'
    Assert ((Get-Content -LiteralPath $planFile -Raw) -eq $before) 'Reload must not rewrite the locked plan'
    Assert ((Get-Item -LiteralPath $planFile).LastWriteTimeUtc -eq $stamp) 'Reload must reuse the persisted file'
    $early = Get-CollabWakeup -Actor lw-liuwang -StateRoot $planRoot -Now '2026-11-17T08:30:00+08:00'
    Assert ($early.nextAt -eq $locked.times[0]) 'Morning planner must select the first slot'
    $next = Get-CollabWakeup -Actor lw-liuwang -StateRoot $planRoot -Now $locked.times[0]
    Assert ($next.nextAt -eq $locked.times[1]) 'A fired slot must advance to the next one'
    $late = Get-CollabWakeup -Actor lw-liuwang -StateRoot $planRoot -Now '2026-11-17T23:00:00+08:00'
    Assert ($late.planDate -eq '2026-11-18') 'Night must advance to tomorrow without catch-up'
    $resume = Get-CollabWakeup -Actor lw-liuwang -StateRoot $planRoot -Now '2026-11-17T16:00:00+08:00'
    Assert ([DateTimeOffset]$resume.nextAt -gt [DateTimeOffset]'2026-11-17T16:00:00+08:00') 'Resume must skip missed slots'
    Assert ($resume.rrule -notmatch ',') 'Next recurrence must contain one hour and one minute'
} finally {
    Get-ChildItem -LiteralPath $planRoot -File -ErrorAction SilentlyContinue | Remove-Item
    if (Test-Path -LiteralPath $planRoot) { Remove-Item -LiteralPath $planRoot }
}

$global:collabTestUser = 'lw-liuwang'
$global:collabTestPages = [Collections.Generic.List[int]]::new()
function global:gh {
    if ($args[1] -eq 'user') { @{login=$global:collabTestUser; id=1} | ConvertTo-Json -Compress }
    else {
        $page = [int]([regex]::Match($args[1], '&page=(\d+)').Groups[1].Value)
        $global:collabTestPages.Add($page)
        $items = if ($page -eq 1) {
            @(1..100 | ForEach-Object { @{number=$_; user=@{login='lw-liuwang'}; assignees=@(@{login='ZicongHe2002'}); body='handoff'} })
        } else {
            @(
                @{number=101; user=@{login='ZicongHe2002'}; assignees=@(@{login='lw-liuwang'}); body='review-pr'},
                @{number=102; user=@{login='outsider'}; assignees=@(@{login='lw-liuwang'}); body='ignore'},
                @{number=103; user=@{login='lw-liuwang'}; assignees=@(); body='needs assignment'}
            )
        }
        ConvertTo-Json -InputObject $items -Depth 8 -Compress
    }
    $global:LASTEXITCODE = 0
}
try {
    $null = Assert-CollabIdentity -Actor lw-liuwang
    $global:collabTestUser = 'ZicongHe2002'
    $rejected = $false
    try { $null = Assert-CollabIdentity -Actor lw-liuwang } catch { $rejected = $true }
    Assert $rejected 'Mismatched identity must be detected'
    $inbox = Get-CollabInbox -Actor lw-liuwang
    Assert (($global:collabTestPages -join ',') -eq '1,2') 'Inbox must paginate beyond 100 items'
    Assert ($inbox.actionRequired.Count -eq 1 -and $inbox.actionRequired[0].number -eq 101) 'Incorrect actionable inbox'
    Assert ($inbox.waitingOnPeer.Count -eq 100) 'Waiting tasks must remain distinct'
    Assert ($inbox.unassigned.Count -eq 1) 'Unassigned handoff must be visible'
} finally {
    Remove-Item Function:/gh
    Remove-Variable collabTestUser,collabTestPages -Scope Global
}
'PASS: schedule invariants, repeatability, identity, full pagination and inbox routing'
