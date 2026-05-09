param(
    [switch]$Lan,
    [switch]$AutoRun,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $root ".env"
$stateDir = Join-Path $root "state"
$pidFile = Join-Path $stateDir "autotrading-web.pid"
$outLog = Join-Path $stateDir "autotrading-web.out.log"
$errLog = Join-Path $stateDir "autotrading-web.err.log"
$hostName = if ($Lan) { "0.0.0.0" } else { "127.0.0.1" }

if (-not (Test-Path -LiteralPath $envFile)) {
    throw ".env file was not found: $envFile"
}

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $existing = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    Write-Host "Autotrading server already appears to be listening on port $Port."
    if ($existing) {
        Write-Host "PID: $($existing.Id) ($($existing.ProcessName))"
    }
    Write-Host "Local URL:  http://127.0.0.1:$Port/"
    exit 0
}

$env:AUTOTRADING_ENV_FILE = $envFile
$env:AUTOTRADING_HOST = $hostName
$env:AUTOTRADING_PORT = "$Port"
if ($AutoRun) {
    $env:AUTO_RUN_ENABLED = "true"
}

$process = Start-Process `
    -FilePath "python" `
    -ArgumentList "-m", "upbit_autotrader.web" `
    -WorkingDirectory $root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -PassThru

Set-Content -Path $pidFile -Value $process.Id -Encoding ascii
Start-Sleep -Seconds 3

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 10 | Out-Null
    Write-Host "Autotrading server started."
} catch {
    Write-Host "Server process started, but health check did not respond yet."
    Write-Host "Check log: $errLog"
}

Write-Host "PID:        $($process.Id)"
Write-Host "Mode:       $(if ($AutoRun) { 'paper autorun enabled' } else { 'manual paper mode' })"
Write-Host "Local URL:  http://127.0.0.1:$Port/"

if ($Lan) {
    $ips = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object -ExpandProperty IPAddress
    foreach ($ip in $ips) {
        Write-Host "Mobile URL: http://$ip`:$Port/"
    }
    Write-Host "If mobile cannot connect, allow port $Port in Windows Firewall for Private networks."
}
