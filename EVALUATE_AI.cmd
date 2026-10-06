@echo off
cd /d "%~dp0"
if exist NextSet.exe (
  NextSet.exe --evaluate-ai
) else (
  set "PYTHONPATH=%~dp0.packages"
  py -3.12 launcher.py --evaluate-ai
)
pause
