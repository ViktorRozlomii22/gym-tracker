@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
if exist NextSet.exe (
  NextSet.exe
  exit /b
)
set "PYTHONUTF8=1"
set "PYTHONPATH=%~dp0.packages"
set "NEXTSET_PY="
py -3.12 -c "import sys; assert sys.version_info >= (3,12)" >nul 2>&1
if not errorlevel 1 set "NEXTSET_PY=py -3.12"
if not defined NEXTSET_PY (
  python -c "import sys; assert (3,12) <= sys.version_info[:2] < (3,14)" >nul 2>&1
  if not errorlevel 1 set "NEXTSET_PY=python"
)
if not defined NEXTSET_PY (
  echo Python was not found. For the easiest setup, download the Windows app ZIP.
  echo For source mode, install Python 3.12 from https://www.python.org/downloads/windows/
  echo Then double-click START.cmd again.
  pause
  exit /b 1
)
if not exist data\cache\setup mkdir data\cache\setup
set "TEMP=%~dp0data\cache\setup"
set "TMP=%~dp0data\cache\setup"
%NEXTSET_PY% launcher.py --check >nul 2>&1
if errorlevel 1 (
  echo Installing local dependencies. First start may take a few minutes...
  %NEXTSET_PY% -m pip install --no-cache-dir --target .packages -r requirements.lock
  if errorlevel 1 goto failed
)
%NEXTSET_PY% launcher.py
exit /b
:failed
echo Setup failed. Check your internet connection and try again.
pause
exit /b 1
