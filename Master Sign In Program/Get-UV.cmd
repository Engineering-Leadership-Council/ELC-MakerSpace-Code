@echo off
setlocal
REM Pass-thru to PowerShell. Example:
REM   Get-UV.cmd -Version v0.4.21 -Dest ".\tools"

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" (
  echo [ERROR] PowerShell not found.
  exit /b 1
)

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0Get-UV.ps1" %*
set "RC=%ERRORLEVEL%"
if %RC% NEQ 0 (
  echo [ERROR] Get-UV failed with code %RC%.
  pause
)
exit /b %RC%