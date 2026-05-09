param(
    [string[]]$TaskNames = @("UpbitAutotradingLocal", "UpbitAutotradingWatchdog")
)

$ErrorActionPreference = "Stop"

foreach ($taskName in $TaskNames) {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Host "${taskName}: not registered"
        continue
    }

    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed scheduled task: $taskName"
}
