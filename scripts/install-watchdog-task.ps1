param(
    [string]$TaskName = "UpbitAutotradingWatchdog",
    [int]$Port = 8000,
    [int]$IntervalMinutes = 5,
    [switch]$Restart,
    [switch]$Lan,
    [switch]$AutoRun
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1) {
    throw "IntervalMinutes must be at least 1."
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$watchdogScript = Join-Path $PSScriptRoot "watchdog-local.ps1"

if (-not (Test-Path -LiteralPath $watchdogScript)) {
    throw "watchdog-local.ps1 was not found: $watchdogScript"
}

$argumentText = "-NoProfile -ExecutionPolicy Bypass -File `"$watchdogScript`" -Port $Port"
if ($Restart) {
    $argumentText += " -Restart"
}
if ($Lan) {
    $argumentText += " -Lan"
}
if ($AutoRun) {
    $argumentText += " -AutoRun"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argumentText -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Check the local Upbit autotrading dashboard health and optionally restart it." `
    -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Action: powershell.exe $argumentText"
