param(
    [string]$TaskName = "UpbitAutotradingLocal",
    [int]$Port = 8000,
    [switch]$Lan,
    [switch]$NoAutoRun
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$startScript = Join-Path $PSScriptRoot "start-local.ps1"

if (-not (Test-Path -LiteralPath $startScript)) {
    throw "start-local.ps1 was not found: $startScript"
}

$argumentText = "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`" -Port $Port"
if ($Lan) {
    $argumentText += " -Lan"
}
if (-not $NoAutoRun) {
    $argumentText += " -AutoRun"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argumentText -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Start the local Upbit autotrading dashboard at Windows logon." `
    -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Action: powershell.exe $argumentText"
