@echo off
setlocal
title Strata - largest context window that fits
cd /d "%~dp0"

set "PYTHON=%~dp0.venv\bin\python.exe"
if not exist "%PYTHON%" set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

rem Computes the context window from the GPU memory that is free right now (see tools\strata_fit_launch.py), then starts Strata.
rem Usage: run-strata-fit.bat [configs\strata-coder-iq1_m.json] [extra options, e.g. --dry-run, --verify, --no-fast, --always-start]
rem Profiles (configs\profiles.json): run-strata-fit.bat --profile quality|big-context|fastest, or the shortcuts run-strata-quality.bat, run-strata-big-context.bat, run-strata-fastest.bat. Fast mode is on by default.
if /i "%~1"=="--profile" goto profile
set "CFG=%~1"
if "%CFG%"=="" set "CFG=%~dp0configs\strata-iq3_xxs.json"
"%PYTHON%" "%~dp0tools\strata_fit_launch.py" --config "%CFG%" %2 %3 %4 %5 %6
if errorlevel 1 pause
goto :eof

:profile
"%PYTHON%" "%~dp0tools\strata_fit_launch.py" %*
if errorlevel 1 pause
