#Requires -Version 7.0
param(
    [Parameter(Mandatory)][ValidateSet('Doctor','Inbox','Plan','Next')][string]$Action,
    [Parameter(Mandatory)][ValidateSet('lw-liuwang','ZicongHe2002')][string]$Actor,
    [string]$Date
)
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'Collab.psm1') -Force
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
switch ($Action) {
    Doctor {
        foreach ($tool in @('git','gh','pwsh')) { $null = Get-Command $tool -ErrorAction Stop }
        $user = Assert-CollabIdentity -Actor $Actor
        [pscustomobject]@{ actor=$user.login; id=$user.id; git=(& git --version); gh=(& gh --version | Select-Object -First 1); powershell=$PSVersionTable.PSVersion.ToString() } | ConvertTo-Json
    }
    Inbox {
        $null = Assert-CollabIdentity -Actor $Actor
        Get-CollabInbox -Actor $Actor | ConvertTo-Json -Depth 30
    }
    Plan {
        $params = @{Actor=$Actor; StateRoot=(Join-Path $repoRoot '.local/plans')}
        if ($Date) { $params.Date=$Date }
        else { $params.Date = [TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTimeOffset]::UtcNow, 'Asia/Shanghai').ToString('yyyy-MM-dd') }
        Get-LockedCollabPlan @params | ConvertTo-Json -Depth 8
    }
    Next {
        Get-CollabWakeup -Actor $Actor -StateRoot (Join-Path $repoRoot '.local/plans') | ConvertTo-Json -Depth 8
    }
}
