@echo off
title Cloudflare Tunnel - quantumsurge.mycpuinfo.com
echo Starting Cloudflare Tunnel...
cd /d "C:\Users\mvsla\Downloads\QuantumSurgeCodeDownloads"
cloudflared.exe tunnel --config "cloudflared-config.yml" run quantumsurge
pause