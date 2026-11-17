Set-StrictMode -Version Latest

function Get-CollabConfig {
    Get-Content (Join-Path $PSScriptRoot '../references/config.json') -Raw | ConvertFrom-Json
}

function Invoke-GhJson {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $output = & gh @Arguments
    if ($LASTEXITCODE -ne 0) { throw "gh failed (exit $LASTEXITCODE): $($Arguments[0])" }
    if ($output) { ($output -join "`n") | ConvertFrom-Json }
}

function Assert-CollabIdentity {
    param([Parameter(Mandatory)][string]$Actor)
    $config = Get-CollabConfig
    if ($Actor -notin $config.actors) { throw "Unknown participant: $Actor" }
    $user = Invoke-GhJson -Arguments @('api', 'user')
    if ($user.login -cne $Actor) { throw "Expected $Actor; gh is authenticated as $($user.login)" }
    $user
}

function New-CollabPlan {
    param(
        [Parameter(Mandatory)][string]$Actor,
        [string]$Date = ([TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTimeOffset]::UtcNow, 'Asia/Shanghai').ToString('yyyy-MM-dd'))
    )
    $config = Get-CollabConfig
    if ($Actor -notin $config.actors) { throw "Unknown participant: $Actor" }
    $null = [DateTime]::ParseExact($Date, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
    $actorOffset = [array]::IndexOf($config.actors, $Actor) * $config.peerOffsetMinutes
    $midnight = [DateTimeOffset]::ParseExact("${Date}T00:00:00+08:00", "yyyy-MM-dd'T'HH:mm:sszzz", [Globalization.CultureInfo]::InvariantCulture)
    $times = @(
        for ($slot = 0; $slot -lt $config.windowsPerDay; $slot++) {
            $key = "$Date|$($config.protocolVersion)|$slot"
            $hash = [Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($key))
            # Explicit byte order keeps both Windows machines on the same plan.
            $sample = [uint32]$hash[0] * 16777216 + [uint32]$hash[1] * 65536 + [uint32]$hash[2] * 256 + [uint32]$hash[3]
            $jitter = $config.minuteMin + $sample % ($config.minuteMax - $config.minuteMin + 1)
            $at = $midnight.AddMinutes($config.firstHour * 60 + $slot * $config.intervalMinutes + $jitter + $actorOffset)
            $at.ToString("yyyy-MM-dd'T'HH:mm:sszzz")
        }
    )
    [pscustomobject]@{
        actor = $Actor
        protocolVersion = $config.protocolVersion
        date = $Date
        timezone = $config.timezone
        times = $times
        targetRunMinutes = $config.targetRunMinutes
        maxRunMinutes = $config.maxRunMinutes
    }
}

function Get-LockedCollabPlan {
    param(
        [Parameter(Mandatory)][string]$Actor,
        [Parameter(Mandatory)][string]$Date,
        [Parameter(Mandatory)][string]$StateRoot
    )
    $config = Get-CollabConfig
    if ($Actor -notin $config.actors) { throw "Unknown participant: $Actor" }
    $null = [DateTime]::ParseExact($Date, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
    $path = Join-Path $StateRoot "$Actor-$Date.json"
    if (Test-Path -LiteralPath $path) {
        $parse = @{ InputObject = Get-Content -LiteralPath $path -Raw }
        if ((Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')) { $parse.DateKind = 'String' }
        $saved = ConvertFrom-Json @parse
        if ($saved.actor -eq $Actor -and $saved.protocolVersion -eq $config.protocolVersion) { return $saved }
    }
    $plan = New-CollabPlan -Actor $Actor -Date $Date
    $null = New-Item -ItemType Directory -Force $StateRoot
    $plan | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $path -Encoding utf8
    $plan
}

function Get-CollabWakeup {
    param(
        [Parameter(Mandatory)][string]$Actor,
        [Parameter(Mandatory)][string]$StateRoot,
        [DateTimeOffset]$Now = [DateTimeOffset]::UtcNow
    )
    $local = [TimeZoneInfo]::ConvertTimeBySystemTimeZoneId($Now, 'Asia/Shanghai')
    foreach ($dayOffset in 0..1) {
        $date = $local.AddDays($dayOffset).ToString('yyyy-MM-dd')
        $plan = Get-LockedCollabPlan -Actor $Actor -Date $date -StateRoot $StateRoot
        foreach ($time in $plan.times) {
            $at = [DateTimeOffset]::Parse($time)
            if ($at -gt $Now) {
                return [pscustomobject]@{
                    actor = $Actor
                    protocolVersion = $plan.protocolVersion
                    planDate = $plan.date
                    nextAt = $at.ToString("yyyy-MM-dd'T'HH:mm:sszzz")
                    timezone = $plan.timezone
                    rrule = "RRULE:FREQ=DAILY;BYHOUR=$($at.Hour);BYMINUTE=$($at.Minute);BYSECOND=0"
                }
            }
        }
    }
    throw 'No future wakeup in the current or next day plan'
}

function Get-CollabInbox {
    param([Parameter(Mandatory)][string]$Actor)
    $config = Get-CollabConfig
    if ($Actor -notin $config.actors) { throw "Unknown participant: $Actor" }
    $issues = [Collections.Generic.List[object]]::new()
    $page = 1
    do {
        $batch = @(Invoke-GhJson -Arguments @('api', "repos/$($config.hub)/issues?state=open&labels=handoff&per_page=100&page=$page"))
        foreach ($issue in $batch) {
            if (-not $issue.PSObject.Properties['pull_request'] -and $issue.user.login -in $config.actors) {
                $issues.Add($issue)
            }
        }
        $page++
    } while ($batch.Count -eq 100)
    [pscustomobject]@{
        actor = $Actor
        actionRequired = @($issues | Where-Object { $Actor -in @($_.assignees | ForEach-Object { $_.login }) })
        waitingOnPeer = @($issues | Where-Object {
            $_.user.login -eq $Actor -and $Actor -notin @($_.assignees | ForEach-Object { $_.login }) -and
            @($_.assignees | Where-Object { $_.login -in $config.actors }).Count -gt 0
        })
        unassigned = @($issues | Where-Object { @($_.assignees).Count -eq 0 })
    }
}

Export-ModuleMember -Function Get-CollabConfig, Invoke-GhJson, Assert-CollabIdentity, New-CollabPlan, Get-LockedCollabPlan, Get-CollabWakeup, Get-CollabInbox
