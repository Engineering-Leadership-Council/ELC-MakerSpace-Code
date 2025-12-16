@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ─────────────────────────── title & color (debug only) ───────────────────────────
title ELC Launcher (portable uv + managed Python)
color 0a

rem ───────────────────────────── config ─────────────────────────────
set "PYFILE=tk_sign.py"
set "UV_VERSION=v0.4.21"   rem Pin a known-good version for reproducibility

rem Auto-detect arch for the right uv asset
set "ARCH=x86_64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARCH=aarch64"

rem Where to put uv.exe (portable, next to this script)
set "DIR=%~dp0"
set "UVEXE=%DIR%uv.exe"
set "UVZIP=%TEMP%\uv_portable.zip"
set "UV_ZIP_URL=https://github.com/astral-sh/uv/releases/download/%UV_VERSION%/uv-%ARCH%-pc-windows-msvc.zip"

rem Logs
set "RUN_LOG=%DIR%run_output.log"
set "ERR_LOG=%DIR%tk_sign_error.log"

rem ───────────────────────────── intro ─────────────────────────────
cd /d "%DIR%"
del /f /q "%RUN_LOG%" >nul 2>&1

echo.
echo === ELC Launcher starting in: %DIR%
echo === Python script: %PYFILE%
echo.

rem ─────────────────────── sanity: python file exists ───────────────────────
if not exist "%PYFILE%" (
  echo [ERROR] "%PYFILE%" not found next to this launcher.
  goto :fail
)

rem ─────────────────────── ensure uv.exe (portable) ───────────────────────
if not exist "%UVEXE%" (
  echo [INFO] uv.exe not found; downloading portable zip for %ARCH%...
  del /f /q "%UVZIP%" >nul 2>&1

  rem Use whatever is available: curl, PowerShell, or certutil
  where curl >nul 2>&1
  if not errorlevel 1 (
    curl -fL -o "%UVZIP%" "%UV_ZIP_URL%"
  ) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "try { (New-Object Net.WebClient).DownloadFile('%UV_ZIP_URL%','%UVZIP%'); exit 0 } catch { exit 1 }"
    if errorlevel 1 (
      certutil -urlcache -split -f "%UV_ZIP_URL%" "%UVZIP%" >nul 2>&1
    )
  )

  if not exist "%UVZIP%" (
    echo [ERROR] Could not download uv from:
    echo        %UV_ZIP_URL%
    goto :fail
  )

  rem Extract zip (PowerShell preferred; fallback to tar if available)
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "try { Expand-Archive -Path '%UVZIP%' -DestinationPath '%DIR%' -Force; exit 0 } catch { exit 1 }"
  if errorlevel 1 (
    where tar >nul 2>&1 && tar -xf "%UVZIP%" -C "%DIR%"
  )

  if not exist "%UVEXE%" (
    echo [ERROR] uv.exe not found after extraction. Place uv.exe next to this file and retry.
    goto :fail
  )
)

echo [INFO] Using uv: %UVEXE%

rem ─────────────────────── run app (managed Python via uv) ───────────────────────
echo.
echo === Running: "%UVEXE%" run --python-preference=managed "%PYFILE%"
echo    (stdout+stderr will also be logged to run_output.log)
echo.

rem Use PowerShell Tee-Object (this is PowerShell’s, not CMD’s tee)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$env:UVEXE='%UVEXE%'; $env:PYFILE='%PYFILE%'; $env:RUN_LOG='%RUN_LOG%';" ^
  "& '%UVEXE%' run --python-preference=managed '%PYFILE%' 2>&1 | Tee-Object -FilePath $env:RUN_LOG -Append; " ^
  "exit $LASTEXITCODE"

set "RC=%ERRORLEVEL%"

echo.
if %RC% NEQ 0 (
  echo === Process exited with code %RC% ===
  echo See "%RUN_LOG%" for full output and "%ERR_LOG%" if your script writes there.
  goto :fail_with_popup
) else (
  echo === Done (exit code 0) ===
  goto :eof
)

rem ─────────────────────────── failure handlers ───────────────────────────
:fail_with_popup
rem Pop a GUI alert (no console required) and open the log for quick debugging
rem mshta is present on stock Windows and shows a minimal dialog
mshta "javascript:alert('ELC Launcher failed (code %RC%).%0D%0ASee run_output.log for details.');close()"
start "" notepad.exe "%RUN_LOG%"
exit /b %RC%

:fail
rem Generic fail point (console visible)
echo.
echo (Press any key to close...)
pause >nul
exit /b 1