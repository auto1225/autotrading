param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pidFile = Join-Path $root "state\autotrading-web.pid"
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $listener) {
    Write-Host "Autotrading server is not listening on port $Port."
    exit 1
}

$process = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
$recordedPid = if (Test-Path -LiteralPath $pidFile) { (Get-Content -Path $pidFile -Raw).Trim() } else { "" }

Write-Host "Autotrading server is running."
Write-Host "Listening:  $($listener.LocalAddress):$($listener.LocalPort)"
if ($process) {
    Write-Host "PID:        $($process.Id) ($($process.ProcessName))"
}
if ($recordedPid) {
    Write-Host "PID file:   $recordedPid"
}

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 10
    Write-Host "Health:     $($health.status)"
} catch {
    Write-Host "Health:     no response"
}

Write-Host "Local URL:  http://127.0.0.1:$Port/"

if ($listener.LocalAddress -eq "0.0.0.0" -or $listener.LocalAddress -eq "::" -or $listener.LocalAddress -notlike "127.*") {
    $ips = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object -ExpandProperty IPAddress
    foreach ($ip in $ips) {
        Write-Host "LAN URL:    http://$ip`:$Port/"
    }
} else {
    Write-Host "LAN URL:    not active; restart with .\scripts\start-local.ps1 -Lan"
}
