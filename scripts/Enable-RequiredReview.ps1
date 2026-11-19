#Requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('A','B')][string]$Actor,
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'

function Invoke-RequiredReviewGh {
    param([string]$Endpoint, [string]$Method = 'GET', [string]$InputPath)
    $arguments = @('api', '--method', $Method, $Endpoint)
    if ($InputPath) { $arguments += @('--input', $InputPath) }
    $previousPreference = $ErrorActionPreference
    try {
        # Windows PowerShell can turn native stderr into nonterminating errors.
        $ErrorActionPreference = 'Continue'
        $output = @(& gh @arguments 2>&1)
        $exitCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    $text = ($output | ForEach-Object { $_.ToString() }) -join "`n"
    if ($exitCode -ne 0) { throw "gh $Method $Endpoint failed: $text" }
    if ($text.Trim()) {
        $parsed = $text | ConvertFrom-Json
        # Explicit enumeration keeps JSON arrays consistent in PowerShell 5.1/7.
        foreach ($item in @($parsed)) { $item }
    }
}

function Assert-RequiredReviewWindow {
    $now = ([DateTimeOffset](Get-Date)).ToUniversalTime().ToOffset([TimeSpan]::FromHours(8))
    if ($now.Hour -lt 9 -or $now.Hour -ge 23) {
        throw 'GitHub writes are allowed only from 09:00 until 23:00 Asia/Shanghai. Use -PlanOnly for a read-only check.'
    }
}

function Test-RequiredReviewMatch {
    param($Actual, $Desired)
    if ($null -eq $Desired) { return $null -eq $Actual }
    if ($null -eq $Actual) { return $false }
    if ($Desired -is [pscustomobject]) {
        foreach ($property in $Desired.PSObject.Properties) {
            $observed = $Actual.PSObject.Properties[$property.Name]
            if ($null -eq $observed -or -not (Test-RequiredReviewMatch -Actual $observed.Value -Desired $property.Value)) {
                return $false
            }
        }
        return $true
    }
    if ($Desired -is [array]) {
        if ($Actual -isnot [array] -or $Actual.Count -ne $Desired.Count) { return $false }
        for ($index = 0; $index -lt $Desired.Count; $index++) {
            if (-not (Test-RequiredReviewMatch -Actual $Actual[$index] -Desired $Desired[$index])) { return $false }
        }
        return $true
    }
    return $Actual -ceq $Desired
}

function Get-RequiredReviewPages {
    param([string]$Endpoint)
    $separator = if ($Endpoint.Contains('?')) { '&' } else { '?' }
    $page = 1
    do {
        $items = @(Invoke-RequiredReviewGh -Endpoint "${Endpoint}${separator}per_page=100&page=$page")
        $items
        $page++
    } while ($items.Count -eq 100)
}

function Get-RequiredReviewRulesets {
    param([string]$Repository)
    Get-RequiredReviewPages -Endpoint "repos/$Repository/rulesets?includes_parents=false"
}

function Get-RequiredReviewManagedRule {
    param([string]$Repository, [string]$Name)
    $managedRules = @(Get-RequiredReviewRulesets -Repository $Repository | Where-Object { $_.name -ceq $Name })
    if ($managedRules.Count -gt 1) { throw "Multiple rulesets named '$Name' exist in $Repository; no rule was changed." }
    if ($managedRules.Count -eq 1) {
        Invoke-RequiredReviewGh -Endpoint "repos/$Repository/rulesets/$($managedRules[0].id)"
    }
}

function Invoke-RequiredReviewSetup {
    param([Parameter(Mandatory)][ValidateSet('A','B')][string]$Actor, [switch]$PlanOnly)
    $accounts = @{ A = 'lw-liuwang'; B = 'ZicongHe2002' }
    $repositories = @{ A = 'lw-liuwang/cs336-notes'; B = 'ZicongHe2002/rsi-notes' }
    $repository = $repositories[$Actor]
    $managedName = 'Require reviewed pull requests'
    $templatePath = Join-Path $PSScriptRoot '../config/required-review-ruleset.json'
    $desired = Get-Content -LiteralPath $templatePath -Raw | ConvertFrom-Json
    if ($desired.name -cne $managedName) { throw 'Unexpected managed ruleset template name.' }
    $user = Invoke-RequiredReviewGh -Endpoint 'user'
    if ($user.login -cne $accounts[$Actor]) { throw "Expected gh identity $($accounts[$Actor]); found $($user.login)." }
    $repo = Invoke-RequiredReviewGh -Endpoint "repos/$repository"
    if ($repo.full_name -cne $repository -or -not $repo.permissions.admin) {
        throw "The current gh account must have admin permission on $repository."
    }
    $current = Get-RequiredReviewManagedRule -Repository $repository -Name $managedName
    $action = if ($null -eq $current) { 'Create' } elseif (Test-RequiredReviewMatch -Actual $current -Desired $desired) { 'None' } else { 'Update' }
    $recoveredWrite = $false
    if (-not $PlanOnly -and $action -ne 'None') {
        Assert-RequiredReviewWindow
        $inputPath = [IO.Path]::GetTempFileName()
        $writeError = $null
        try {
            [IO.File]::WriteAllText($inputPath, ($desired | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
            $method = if ($action -eq 'Create') { 'POST' } else { 'PUT' }
            $endpoint = "repos/$repository/rulesets"
            if ($action -eq 'Update') { $endpoint += "/$($current.id)" }
            try { $null = Invoke-RequiredReviewGh -Endpoint $endpoint -Method $method -InputPath $inputPath }
            catch { $writeError = $_.Exception.Message }
        } finally { Remove-Item -LiteralPath $inputPath -Force }
        # A failed response may still have applied; read before any possible retry.
        $current = Get-RequiredReviewManagedRule -Repository $repository -Name $managedName
        if ($null -eq $current -or -not (Test-RequiredReviewMatch -Actual $current -Desired $desired)) {
            throw "The GitHub write could not be confirmed. No second write was attempted. $writeError"
        }
        $recoveredWrite = $null -ne $writeError
    }
    $branch = [Uri]::EscapeDataString($repo.default_branch)
    $effective = @(Get-RequiredReviewPages -Endpoint "repos/$repository/rules/branches/$branch")
    $effectiveManaged = @($effective | Where-Object { $null -ne $current -and $_.ruleset_id -eq $current.id -and $_.type -eq 'pull_request' })
    $effectiveMatches = $effectiveManaged.Count -eq 1 -and (Test-RequiredReviewMatch -Actual $effectiveManaged[0].parameters -Desired $desired.rules[0].parameters)
    $cannotBypass = $null -ne $current -and $current.enforcement -eq 'active' -and @($current.bypass_actors).Count -eq 0 -and $current.current_user_can_bypass -eq 'never' -and $effectiveMatches
    if (-not $PlanOnly -and (-not $effectiveMatches -or -not $cannotBypass)) {
        throw 'The managed ruleset was read back, but the effective branch rule or current no-bypass status could not be confirmed.'
    }
    $url = if ($null -ne $current) { "https://github.com/$repository/rules/$($current.id)" } else { "https://github.com/$repository/settings/rules" }
    [pscustomobject]@{
        actor = $Actor; identity = $user.login; repository = $repository; defaultBranch = $repo.default_branch
        planOnly = [bool]$PlanOnly; action = $action; changed = (-not $PlanOnly -and $action -ne 'None')
        recoveredAfterWriteError = $recoveredWrite; rulesetUrl = $url
        targetRequiredApprovals = $desired.rules[0].parameters.required_approving_review_count
        requiredApprovals = if ($effectiveManaged.Count -eq 1) { $effectiveManaged[0].parameters.required_approving_review_count } else { $null }
        bypassActors = @(if ($null -ne $current) { $current.bypass_actors })
        currentUserCanBypass = if ($null -ne $current) { $current.current_user_can_bypass } else { $null }
        currentCannotBypassManagedRule = [bool]$cannotBypass; effectiveManagedRuleMatches = [bool]$effectiveMatches
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    if (-not $Actor) { throw 'Specify -Actor A or -Actor B; each actor can configure only their own repository.' }
    Invoke-RequiredReviewSetup -Actor $Actor -PlanOnly:$PlanOnly | ConvertTo-Json -Depth 20
}
