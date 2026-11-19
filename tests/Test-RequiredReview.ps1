#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../scripts/Enable-RequiredReview.ps1')
$templatePath = Join-Path $PSScriptRoot '../config/required-review-ruleset.json'
$templateJson = Get-Content -LiteralPath $templatePath -Raw

function Assert-ReviewTest($Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function New-ReviewTestRule([int]$Id = 42, [int]$Approvals = 1, [string]$Name = 'Require reviewed pull requests') {
    $rule = $templateJson | ConvertFrom-Json
    $rule.name = $Name
    $rule.rules[0].parameters.required_approving_review_count = $Approvals
    $rule | Add-Member -NotePropertyName id -NotePropertyValue $Id
    $rule | Add-Member -NotePropertyName current_user_can_bypass -NotePropertyValue 'never'
    # These fields are added by GitHub even though the request omits them.
    $rule.rules[0].parameters | Add-Member -NotePropertyName required_reviewers -NotePropertyValue @()
    $rule.rules[0].parameters | Add-Member -NotePropertyName require_extra_approval_for_unattributed_changes -NotePropertyValue $true
    $rule
}

function Reset-ReviewTest {
    $global:requiredReviewTest = @{
        Login = 'lw-liuwang'; Repository = 'lw-liuwang/cs336-notes'; Admin = $true
        Now = [DateTimeOffset]'2026-11-19T10:00:00+08:00'; List = @(); Stored = @{}
        Calls = [Collections.Generic.List[object]]::new(); WriteMode = 'Success'; Effective = $true; ExtraEffective = @()
    }
}

function Set-ReviewTestRule($Rule) {
    $global:requiredReviewTest.List += [pscustomobject]@{ id = $Rule.id; name = $Rule.name }
    $global:requiredReviewTest.Stored[$Rule.id] = $Rule
}

function Get-ReviewTestWrites {
    @($global:requiredReviewTest.Calls | Where-Object { $_.Method -ne 'GET' })
}

function Assert-ReviewTestBlocked([scriptblock]$Action, [string]$Message) {
    $blocked = $false
    try { & $Action | Out-Null } catch { $blocked = $true }
    Assert-ReviewTest $blocked $Message
}

function global:Get-Date { $global:requiredReviewTest.Now }
function global:gh {
    $global:LASTEXITCODE = 0
    if ($args[0] -ne 'api' -or $args[1] -ne '--method') { throw "Unexpected gh arguments: $args" }
    $method = $args[2]
    $endpoint = $args[3]
    $state = $global:requiredReviewTest
    $state.Calls.Add([pscustomobject]@{ Method = $method; Endpoint = $endpoint })
    $repoEndpoint = "repos/$($state.Repository)"
    $result = $null
    if ($method -eq 'GET' -and $endpoint -eq 'user') {
        $result = @{ login = $state.Login }
    } elseif ($method -eq 'GET' -and $endpoint -eq $repoEndpoint) {
        $result = @{ full_name = $state.Repository; permissions = @{ admin = $state.Admin }; default_branch = 'main' }
    } elseif ($method -eq 'GET' -and $endpoint.StartsWith("$repoEndpoint/rulesets?includes_parents=false&per_page=100&page=")) {
        $page = [int]([regex]::Match($endpoint, 'page=(\d+)$').Groups[1].Value)
        $result = @($state.List | Select-Object -Skip (($page - 1) * 100) -First 100)
    } elseif ($method -eq 'GET' -and $endpoint.StartsWith("$repoEndpoint/rules/branches/main?per_page=100&page=")) {
        $page = [int]([regex]::Match($endpoint, 'page=(\d+)$').Groups[1].Value)
        $allEffective = @(if ($state.Effective) {
            $state.ExtraEffective
            foreach ($rule in $state.Stored.Values) {
                foreach ($entry in $rule.rules) {
                    [pscustomobject]@{ type = $entry.type; parameters = $entry.parameters; ruleset_id = $rule.id }
                }
            }
        })
        $result = @($allEffective | Select-Object -Skip (($page - 1) * 100) -First 100)
    } elseif ($method -eq 'GET' -and $endpoint.StartsWith("$repoEndpoint/rulesets/")) {
        $id = [int]($endpoint.Split('/')[-1])
        if (-not $state.Stored.ContainsKey($id)) { throw "Unknown ruleset $id" }
        $result = $state.Stored[$id]
    } elseif (($method -eq 'POST' -and $endpoint -eq "$repoEndpoint/rulesets") -or
              ($method -eq 'PUT' -and $endpoint.StartsWith("$repoEndpoint/rulesets/"))) {
        if ($args[4] -ne '--input') { throw 'Mutation must use a payload file.' }
        $payload = Get-Content -LiteralPath $args[5] -Raw | ConvertFrom-Json
        Assert-ReviewTest (($payload | ConvertTo-Json -Depth 30 -Compress) -eq (($templateJson | ConvertFrom-Json) | ConvertTo-Json -Depth 30 -Compress)) 'Payload changed the declared template.'
        if ($state.WriteMode -ne 'FailBeforeApply') {
            $id = if ($method -eq 'POST') { 77 } else { [int]($endpoint.Split('/')[-1]) }
            if ($method -eq 'PUT' -and -not $state.Stored.ContainsKey($id)) { throw 'An unrelated ruleset was updated.' }
            $rule = New-ReviewTestRule -Id $id
            if ($method -eq 'POST') { Set-ReviewTestRule $rule } else { $state.Stored[$id] = $rule }
            $result = $rule
        }
        if ($state.WriteMode -ne 'Success') {
            $global:LASTEXITCODE = 1
            'connection reset'
            return
        }
    } else { throw "Unexpected gh endpoint: $method $endpoint" }
    ConvertTo-Json -InputObject $result -Depth 30 -Compress
}

try {
    Reset-ReviewTest
    $global:requiredReviewTest.Login = 'ZicongHe2002'
    Assert-ReviewTestBlocked { Invoke-RequiredReviewSetup -Actor A } 'Wrong identity was accepted.'
    Assert-ReviewTest (@(Get-ReviewTestWrites).Count -eq 0) 'Wrong identity wrote GitHub.'

    Reset-ReviewTest
    $global:requiredReviewTest.Admin = $false
    Assert-ReviewTestBlocked { Invoke-RequiredReviewSetup -Actor A } 'Missing admin permission was accepted.'
    Assert-ReviewTest (@(Get-ReviewTestWrites).Count -eq 0) 'Missing admin permission wrote GitHub.'

    foreach ($time in @('2026-11-19T08:59:59+08:00','2026-11-19T23:00:00+08:00')) {
        Reset-ReviewTest
        $global:requiredReviewTest.Now = [DateTimeOffset]$time
        Assert-ReviewTestBlocked { Invoke-RequiredReviewSetup -Actor A } 'A write outside Beijing hours was accepted.'
        Assert-ReviewTest (@(Get-ReviewTestWrites).Count -eq 0) 'The time window did not block a mutation.'
        $plan = Invoke-RequiredReviewSetup -Actor A -PlanOnly
        Assert-ReviewTest ($plan.action -eq 'Create' -and -not $plan.changed) 'PlanOnly could not inspect outside write hours.'
        Assert-ReviewTest (@(Get-ReviewTestWrites).Count -eq 0) 'PlanOnly performed a mutation.'
    }

    Reset-ReviewTest
    $global:requiredReviewTest.Now = [DateTimeOffset]'2026-11-19T01:00:00Z'
    $created = Invoke-RequiredReviewSetup -Actor A
    $writes = @(Get-ReviewTestWrites)
    Assert-ReviewTest ($writes.Count -eq 1 -and $writes[0].Method -eq 'POST') 'Creation was not one POST.'
    Assert-ReviewTest ($created.changed -and $created.requiredApprovals -eq 1 -and $created.currentCannotBypassManagedRule) 'Creation was not verified against effective branch rules.'
    Assert-ReviewTest (($created | ConvertTo-Json -Depth 20 | ConvertFrom-Json).bypassActors -is [array]) 'An empty bypass list became null.'
    $again = Invoke-RequiredReviewSetup -Actor A
    Assert-ReviewTest ($again.action -eq 'None' -and -not $again.changed -and @(Get-ReviewTestWrites).Count -eq 1) 'A repeat run wrote again or rejected server-added fields.'

    Reset-ReviewTest
    $global:requiredReviewTest.Login = 'ZicongHe2002'
    $global:requiredReviewTest.Repository = 'ZicongHe2002/rsi-notes'
    $b = Invoke-RequiredReviewSetup -Actor B
    Assert-ReviewTest ($b.repository -eq 'ZicongHe2002/rsi-notes' -and $b.identity -eq 'ZicongHe2002') 'B was not restricted to B repository and identity.'

    Reset-ReviewTest
    $global:requiredReviewTest.List = @(1..100 | ForEach-Object { [pscustomobject]@{ id = $_ + 100; name = "Other rule $_" } })
    Set-ReviewTestRule (New-ReviewTestRule)
    $existing = Invoke-RequiredReviewSetup -Actor A
    $pages = @($global:requiredReviewTest.Calls | Where-Object { $_.Endpoint.Contains('/rulesets?') })
    Assert-ReviewTest ($pages.Count -eq 2 -and $existing.action -eq 'None' -and @(Get-ReviewTestWrites).Count -eq 0) 'Ruleset pagination missed the managed rule after 100 unrelated rules.'

    Reset-ReviewTest
    Set-ReviewTestRule (New-ReviewTestRule)
    $global:requiredReviewTest.ExtraEffective = @(1..101 | ForEach-Object {
        [pscustomobject]@{ type = 'pull_request'; parameters = @{ required_approving_review_count = 4 }; ruleset_id = $_ + 1000 }
    })
    $laterEffective = Invoke-RequiredReviewSetup -Actor A
    $effectivePages = @($global:requiredReviewTest.Calls | Where-Object { $_.Endpoint.Contains('/rules/branches/main?') })
    Assert-ReviewTest ($effectivePages.Count -eq 2 -and $laterEffective.requiredApprovals -eq 1 -and $laterEffective.currentCannotBypassManagedRule) 'Effective-rule pagination missed the managed rule after 101 unrelated rules.'
    Assert-ReviewTest ($laterEffective.action -eq 'None' -and @(Get-ReviewTestWrites).Count -eq 0) 'Reading later effective-rule pages caused a mutation.'

    Reset-ReviewTest
    Set-ReviewTestRule (New-ReviewTestRule -Id 42 -Approvals 0)
    Set-ReviewTestRule (New-ReviewTestRule -Id 99 -Name 'Other policy')
    $unrelatedBefore = $global:requiredReviewTest.Stored[99] | ConvertTo-Json -Depth 30 -Compress
    $updated = Invoke-RequiredReviewSetup -Actor A
    $writes = @(Get-ReviewTestWrites)
    Assert-ReviewTest ($updated.action -eq 'Update' -and $writes.Count -eq 1 -and $writes[0].Method -eq 'PUT' -and $writes[0].Endpoint.EndsWith('/42')) 'Update did not target only the single managed rule.'
    Assert-ReviewTest (($global:requiredReviewTest.Stored[99] | ConvertTo-Json -Depth 30 -Compress) -eq $unrelatedBefore) 'An unrelated policy changed.'

    Reset-ReviewTest
    Set-ReviewTestRule (New-ReviewTestRule -Id 42)
    Set-ReviewTestRule (New-ReviewTestRule -Id 43)
    Assert-ReviewTestBlocked { Invoke-RequiredReviewSetup -Actor A } 'Duplicate managed names were accepted.'
    Assert-ReviewTest (@(Get-ReviewTestWrites).Count -eq 0) 'Duplicate managed names caused a mutation.'

    Reset-ReviewTest
    $global:requiredReviewTest.WriteMode = 'FailAfterApply'
    $recovered = Invoke-RequiredReviewSetup -Actor A
    Assert-ReviewTest ($recovered.recoveredAfterWriteError -and $recovered.currentCannotBypassManagedRule) 'An applied write with a failed response was not recovered by readback.'
    Assert-ReviewTest (@(Get-ReviewTestWrites).Count -eq 1) 'An uncertain applied write was repeated.'

    Reset-ReviewTest
    $global:requiredReviewTest.WriteMode = 'FailBeforeApply'
    Assert-ReviewTestBlocked { Invoke-RequiredReviewSetup -Actor A } 'An unconfirmed failed write was reported as success.'
    Assert-ReviewTest (@(Get-ReviewTestWrites).Count -eq 1) 'A failed write was blindly retried.'

    Reset-ReviewTest
    Set-ReviewTestRule (New-ReviewTestRule)
    $global:requiredReviewTest.Effective = $false
    Assert-ReviewTestBlocked { Invoke-RequiredReviewSetup -Actor A } 'A ruleset absent from effective branch rules was reported as enforced.'

    Reset-ReviewTest
    $bypassRule = New-ReviewTestRule
    $bypassRule.current_user_can_bypass = 'always'
    Set-ReviewTestRule $bypassRule
    Assert-ReviewTestBlocked { Invoke-RequiredReviewSetup -Actor A } 'A bypassable current rule was reported as non-bypassable.'

    'PASS: identity/admin, Beijing window/PlanOnly, A/B repository mapping, full ruleset/effective-rule pagination, create/update/no-op, unrelated rules, duplicates, uncertain-write readback, effective rule and no-bypass verification'
} finally {
    Remove-Item Function:/gh,Function:/Get-Date
    Remove-Variable requiredReviewTest -Scope Global
}
