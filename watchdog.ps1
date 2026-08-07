# QuantumSurge Watchdog v4 - named Cloudflare tunnel (quantumsurge)
$ProjectDir  = "C:\Users\mvsla\Downloads\QuantumSurgeCodeDownloads"
$FlaskLog    = "$ProjectDir\flask.log"
$CFLog       = "$ProjectDir\cloudflared.log"
$OllamaExe   = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$CFExe       = "$ProjectDir\cloudflared.exe"
$CFConfig    = "$ProjectDir\cloudflared-config.yml"
$OriginCert  = "C:\Users\mvsla\.cloudflared\cert.pem"
$TunnelName  = "quantumsurge"
$PublicHost  = "quantumsurge.mycpuinfo.com"

Write-Host "=== QuantumSurge Watchdog v4 Started ===" -ForegroundColor Cyan

while ($true) {
    # --- 1. OLLAMA ---
    $ollama = Get-Process ollama -ErrorAction SilentlyContinue
    if (-not $ollama) {
        Write-Host "[WATCHDOG] Ollama down - restarting..." -ForegroundColor Yellow
        Start-Process $OllamaExe -ArgumentList "serve" -NoNewWindow
        Start-Sleep -Seconds 5
    }

    # --- 2. FLASK ---
    $flaskUp = $false
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:5000" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $flaskUp = $true }
    } catch {}

    if (-not $flaskUp) {
        Write-Host "[WATCHDOG] Flask down - restarting..." -ForegroundColor Yellow
        Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Start-Process "python" -ArgumentList "-m waitress --port=5000 --threads=8 server:app" -WorkingDirectory $ProjectDir -NoNewWindow -RedirectStandardOutput $FlaskLog
        Start-Sleep -Seconds 5
    }

    # --- 3. NAMED CLOUDFLARE TUNNEL ---
    $cf = Get-Process cloudflared -ErrorAction SilentlyContinue
    if (-not $cf) {
        Write-Host "[WATCHDOG] Cloudflare tunnel down - restarting..." -ForegroundColor Yellow
        if (Test-Path $CFExe) {
            if (-not (Test-Path $OriginCert)) {
                Write-Host "[WATCHDOG] Missing $OriginCert - run 'cloudflared tunnel login' once." -ForegroundColor Red
            }
            Start-Process $CFExe -ArgumentList "tunnel","--config",$CFConfig,"run",$TunnelName -WorkingDirectory $ProjectDir -NoNewWindow -RedirectStandardOutput $CFLog
            Start-Sleep -Seconds 8
            Write-Host "[WATCHDOG] Named tunnel $TunnelName serving https://$PublicHost" -ForegroundColor Green
        } else {
            Write-Host "[WATCHDOG] cloudflared.exe missing at $CFExe" -ForegroundColor Red
        }
    }

    Write-Host "[WATCHDOG] OK - $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
    Start-Sleep -Seconds 15
}
