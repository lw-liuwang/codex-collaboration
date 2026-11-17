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
    $seedText = "$Date|$($config.protocolVersion)"
    $hash = [Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($seedText))
    $rng = [Random]::new([BitConverter]::ToInt32($hash, 0) -band [int]::MaxValue)
    $selected = @($config.firstHour..$config.lastHour)
    $actorOffset = [array]::IndexOf($config.actors, $Actor) * $config.peerOffsetMinutes
    $minute = $rng.Next($config.minuteMin, $config.minuteMax + 1) + $actorOffset
    $minutes = @($minute..59 | Where-Object { ($_ - $minute) % $config.intervalMinutes -eq 0 })
    $times = @(
        foreach ($hour in $selected) {
            foreach ($slotMinute in $minutes) { '{0}T{1:00}:{2:00}:00+08:00' -f $Date, $hour, $slotMinute }
        }
    )
    [pscustomobject]@{
        actor = $Actor
        protocolVersion = $config.protocolVersion
        date = $Date
        timezone = $config.timezone
        hours = $selected
        minute = $minute
        minutes = $minutes
        times = $times
        rrule = "RRULE:FREQ=DAILY;BYHOUR=$($selected -join ',');BYMINUTE=$($minutes -join ',');BYSECOND=0"
        targetRunMinutes = $config.targetRunMinutes
        maxRunMinutes = $config.maxRunMinutes
    }
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

Export-ModuleMember -Function Get-CollabConfig, Invoke-GhJson, Assert-CollabIdentity, New-CollabPlan, Get-CollabInbox
