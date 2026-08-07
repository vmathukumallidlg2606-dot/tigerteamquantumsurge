# QuantumSurge - Start Services in Visible Terminals
# This script opens separate PowerShell windows for each service

$ProjectDir = "C:\Users\mvsla\Downloads\QuantumSurgeCodeDownloads"
$OllamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$CFExe = "$ProjectDir\cloudflared.exe"
$CFConfig = "$ProjectDir\cloudflared-config.yml"
$PublicHost = "quantumsurge.mycpuinfo.com"

Write-Host "Starting QuantumSurge Services in Visible Terminals..." -ForegroundColor Cyan

# 1. Ollama Terminal
$ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue
if ($ollamaProcess) {
    Write-Host "[1/3] Ollama is already running (PID: $($ollamaProcess.Id))" -ForegroundColor Yellow
} else {
    Write-Host "[1/3] Starting Ollama in new terminal..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "$OllamaExe serve"
    Start-Sleep -Seconds 3
}

# 2. Flask/Waitress Terminal
$flaskProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*waitress*" }
Write-Host "[2/3] Starting Flask server in new terminal..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir'; python -m waitress --port=5000 --threads=8 server:app"
Start-Sleep -Seconds 5

# 3. Cloudflare Tunnel Terminal
$cfProcess = Get-Process cloudflared -ErrorAction SilentlyContinue
if ($cfProcess) {
    Write-Host "[3/3] Cloudflare tunnel is already running (PID: $($cfProcess.Id))" -ForegroundColor Yellow
} else {
        Write-Host "[3/3] Starting Cloudflare tunnel in new terminal..." -ForegroundColor Green
        if (Test-Path $CFExe) {
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir'; $CFExe tunnel --config `"$CFConfig`" run quantumsurge"
            Start-Sleep -Seconds 3
    } else {
        Write-Host "ERROR: cloudflared.exe not found at $CFExe" -ForegroundColor Red
    }
}

Write-Host "`nAll services started in separate terminals." -ForegroundColor Cyan
Write-Host "Public URL: https://$PublicHost" -ForegroundColor Green
Write-Host "`nPress any key to exit this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")