#Requires -Version 7.0
param(
    [Parameter(Mandatory)][ValidateSet('Doctor','Inbox','Plan')][string]$Action,
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
        $params = @{Actor=$Actor}
        if ($Date) { $params.Date=$Date }
        $plan = New-CollabPlan @params
        $folder = Join-Path $repoRoot '.local/plans'
        $null = New-Item -ItemType Directory -Force $folder
        $json = $plan | ConvertTo-Json -Depth 8
        $json | Set-Content (Join-Path $folder "$Actor-$($plan.date).json") -Encoding utf8
        $json
    }
}
