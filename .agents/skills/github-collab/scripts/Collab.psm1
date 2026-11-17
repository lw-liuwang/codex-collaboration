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
    $seedText = "$Date|$Actor|$($config.protocolVersion)"
    $hash = [Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($seedText))
    $rng = [Random]::new([BitConverter]::ToInt32($hash, 0) -band [int]::MaxValue)
    $hours = [Collections.Generic.List[int]]::new()
    foreach ($hour in $config.firstHour..$config.lastHour) { $hours.Add($hour) }
    for ($i = $hours.Count - 1; $i -gt 0; $i--) {
        $j = $rng.Next($i + 1)
        $temp = $hours[$i]; $hours[$i] = $hours[$j]; $hours[$j] = $temp
    }
    $selected = @($hours | Select-Object -First $config.windowsPerDay | Sort-Object)
    $minute = $rng.Next($config.minuteMin, $config.minuteMax + 1)
    [pscustomobject]@{
        actor = $Actor
        date = $Date
        timezone = $config.timezone
        hours = $selected
        minute = $minute
        times = @($selected | ForEach-Object { '{0}T{1:00}:{2:00}:00+08:00' -f $Date, $_, $minute })
        rrule = "RRULE:FREQ=DAILY;BYHOUR=$($selected -join ',');BYMINUTE=$minute;BYSECOND=0"
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
