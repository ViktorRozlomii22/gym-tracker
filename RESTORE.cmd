@echo off
cd /d "%~dp0"
if exist NextSet.exe (
  NextSet.exe --restore
  exit /b
)
set "PYTHONPATH=%~dp0.packages;%PYTHONPATH%"
where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 launcher.py --restore
) else (
  python launcher.py --restore
)
pause
