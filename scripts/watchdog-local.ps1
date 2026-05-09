param(
    [int]$Port = 8000,
    [switch]$Restart,
    [switch]$Lan,
    [switch]$AutoRun
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stateDir = Join-Path $root "state"
$alertLog = Join-Path $stateDir "watchdog-alerts.jsonl"
$healthUrl = "http://127.0.0.1:$Port/api/health"

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

function Write-WatchdogEvent {
    param(
        [bool]$Ok,
        [string]$Message
    )

    $payload = [ordered]@{
        time = (Get-Date).ToUniversalTime().ToString("o")
        ok = $Ok
        port = $Port
        restartRequested = [bool]$Restart
        message = $Message
    }
    Add-Content -Path $alertLog -Value ($payload | ConvertTo-Json -Compress) -Encoding utf8
}

try {
    Invoke-RestMethod -Uri $healthUrl -TimeoutSec 8 | Out-Null
    Write-Host "Autotrading health check OK: $healthUrl"
    exit 0
} catch {
    $message = "Health check failed: $($_.Exception.Message)"
    Write-Warning $message
    Write-WatchdogEvent -Ok $false -Message $message
}

if ($Restart) {
    $startScript = Join-Path $PSScriptRoot "start-local.ps1"
    $arguments = @("-Port", "$Port")
    if ($Lan) {
        $arguments += "-Lan"
    }
    if ($AutoRun) {
        $arguments += "-AutoRun"
    }
    & $startScript @arguments
    Write-WatchdogEvent -Ok $true -Message "Restart command was issued."
}
