@echo off
title Flask Server - Port 5000
echo Starting Flask/Waitress Server on Port 5000...
cd /d "C:\Users\mvsla\Downloads\QuantumSurgeCodeDownloads"
python -m waitress --port=5000 --threads=8 server:app
pause