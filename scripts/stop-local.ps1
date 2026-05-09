param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pidFile = Join-Path $root "state\autotrading-web.pid"
$targetPid = $null

if (Test-Path -LiteralPath $pidFile) {
    $rawPid = (Get-Content -Path $pidFile -Raw).Trim()
    if ($rawPid -match "^\d+$") {
        $targetPid = [int]$rawPid
    }
}

if (-not $targetPid) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        $targetPid = [int]$listener.OwningProcess
    }
}

if (-not $targetPid) {
    Write-Host "No autotrading server process was found."
    exit 0
}

$process = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
if (-not $process) {
    Write-Host "Recorded process is no longer running: $targetPid"
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    exit 0
}

Stop-Process -Id $targetPid
Start-Sleep -Seconds 1
Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
Write-Host "Stopped autotrading server. PID: $targetPid"
