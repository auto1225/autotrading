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

    $info = Get-ScheduledTaskInfo -TaskName $taskName
    Write-Host "${taskName}: $($task.State)"
    Write-Host "  LastRunTime:  $($info.LastRunTime)"
    Write-Host "  LastTaskResult: $($info.LastTaskResult)"
    Write-Host "  NextRunTime:  $($info.NextRunTime)"
}
