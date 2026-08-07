@echo off
title Ollama Server
echo Starting Ollama Server...
cd /d "%LOCALAPPDATA%\Programs\Ollama"
ollama.exe serve
pause