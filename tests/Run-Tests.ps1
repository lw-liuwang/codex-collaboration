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
    Assert (@($plan.hours | Sort-Object -Unique).Count -eq 14) 'Expected every hour in the daytime window'
    Assert (($plan.hours | Measure-Object -Minimum).Minimum -ge 9 -and ($plan.hours | Measure-Object -Maximum).Maximum -le 22) 'Hours outside window'
    Assert ($plan.minutes.Count -eq 3) 'Expected three slots per hour'
    Assert ($plan.minute -ge 2 -and $plan.minute -le 18) 'Minute outside window'
    for ($i=1; $i -lt $plan.times.Count; $i++) {
        Assert (([DateTimeOffset]$plan.times[$i] - [DateTimeOffset]$plan.times[$i-1]).TotalMinutes -eq 20) 'Wakeups must be exactly twenty minutes apart'
    }
}
Assert (@($plans | Where-Object actor -eq 'lw-liuwang' | ForEach-Object minute | Sort-Object -Unique).Count -ge 4) 'Daily offset should vary'
foreach ($day in 1..28) {
    $date = '2026-11-{0:00}' -f $day
    $a = New-CollabPlan -Actor lw-liuwang -Date $date
    $b = New-CollabPlan -Actor ZicongHe2002 -Date $date
    for ($i=0; $i -lt $a.times.Count; $i++) {
        Assert (([DateTimeOffset]$b.times[$i] - [DateTimeOffset]$a.times[$i]).TotalMinutes -eq 10) 'Actors must alternate with a ten-minute offset'
    }
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
