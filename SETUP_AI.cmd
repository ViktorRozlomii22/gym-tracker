@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
if exist NextSet.exe (
  NextSet.exe --setup-ai
  exit /b
)
set "PYTHONPATH=%~dp0.packages"
set "PYTHONUTF8=1"
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 (
  py -3.12 launcher.py --setup-ai
) else (
  python launcher.py --setup-ai
)
pause
