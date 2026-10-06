@echo off
setlocal
cd /d "%~dp0"
if defined NEXTSET_DATA_DIR (
  if not exist "%NEXTSET_DATA_DIR%" mkdir "%NEXTSET_DATA_DIR%"
  type nul > "%NEXTSET_DATA_DIR%\stop.request"
) else (
  if not exist data mkdir data
  type nul > data\stop.request
)
echo Stop requested. The bot will shut down within a few seconds.
