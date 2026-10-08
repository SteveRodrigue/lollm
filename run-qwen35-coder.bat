@echo off
setlocal
title Qwen 3.5 9B Coder (64K Context) - llama-server
cd /d "%~dp0"

set "SERVER=%~dp0runtimes\llama-cuda-b11093\llama-server.exe"
set "MODEL=%~dp0models\Qwen3.5-9B-Coder-Q3_K_M\Qwen3.5-9B-Coder.Q3_K_M.gguf"

if not exist "%SERVER%" (
    echo [ERROR] llama-server not found at "%SERVER%"
    pause
    exit /b 1
)

if not exist "%MODEL%" (
    echo [ERROR] Model weights not found at "%MODEL%"
    pause
    exit /b 1
)

echo Starting Qwen 3.5 9B Coder on http://127.0.0.1:8080/v1 ...
echo Context size: 65536 tokens (64K) with Flash Attention and 4-bit KV Cache (q4_0)
echo.

"%SERVER%" ^
  -m "%MODEL%" ^
  -ngl 99 ^
  -c 65536 ^
  --flash-attn on ^
  -ctk q4_0 ^
  -ctv q4_0 ^
  --port 8080 ^
  --host 127.0.0.1

if errorlevel 1 pause
