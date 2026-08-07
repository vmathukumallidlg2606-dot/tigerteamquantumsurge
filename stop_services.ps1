# QuantumSurge - Stop All Services
# This script stops all running background services

Write-Host "Stopping QuantumSurge Services..." -ForegroundColor Cyan

# 1. Stop Ollama
$ollama = Get-Process ollama -ErrorAction SilentlyContinue
if ($ollama) {
    Write-Host "[1/3] Stopping Ollama (PID: $($ollama.Id))..." -ForegroundColor Yellow
    $ollama | Stop-Process -Force
} else {
    Write-Host "[1/3] Ollama not running." -ForegroundColor Gray
}

# 2. Stop Flask/Waitress (Python processes running waitress)
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*waitress*" }
if ($pythonProcesses) {
    Write-Host "[2/3] Stopping Flask server..." -ForegroundColor Yellow
    $pythonProcesses | Stop-Process -Force
} else {
    Write-Host "[2/3] Flask server not running." -ForegroundColor Gray
}

# 3. Stop Cloudflare Tunnel
$cf = Get-Process cloudflared -ErrorAction SilentlyContinue
if ($cf) {
    Write-Host "[3/3] Stopping Cloudflare tunnel..." -ForegroundColor Yellow
    $cf | Stop-Process -Force
} else {
    Write-Host "[3/3] Cloudflare tunnel not running." -ForegroundColor Gray
}

Write-Host "`nAll services stopped." -ForegroundColor Green
Write-Host "Press any key to exit this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")