@echo off
setlocal
title Strata - Qwen3.8-Flash-Next IQ2_XS (RAM capped)
cd /d "%~dp0"

set "PYTHON=%~dp0.venv\bin\python.exe"
if not exist "%PYTHON%" set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

"%PYTHON%" "%~dp0runtimes\strata\serve\server.py" --engine strata --config "%~dp0configs\strata-iq2_xs-ramcap.json" --port 8080 --fit-max-tokens
if errorlevel 1 pause
