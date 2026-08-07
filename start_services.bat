@echo off
title QuantumSurge - Start Services in Visible Terminals
echo Starting QuantumSurge Services...
echo.

REM Check if PowerShell script exists
if not exist "%~dp0start_visible_terminals.ps1" (
    echo ERROR: start_visible_terminals.ps1 not found!
    pause
    exit /b 1
)

REM Run PowerShell script with execution policy bypass
PowerShell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_visible_terminals.ps1"

echo.
echo All services should now be running in separate windows.
pause