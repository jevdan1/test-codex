@echo off
chcp 65001 >nul
setlocal ENABLEDELAYEDEXPANSION

rem Optional interactive pausing (set PORTABLE_INTERACTIVE=1 to require keypresses)
set PORTABLE_INTERACTIVE=%PORTABLE_INTERACTIVE%
if /I "%PORTABLE_INTERACTIVE%"=="true" set PORTABLE_INTERACTIVE=1
if /I "%PORTABLE_INTERACTIVE%"=="yes" set PORTABLE_INTERACTIVE=1
if /I "%PORTABLE_INTERACTIVE%"=="on" set PORTABLE_INTERACTIVE=1
if not "%PORTABLE_INTERACTIVE%"=="1" set PORTABLE_INTERACTIVE=0

rem ========== SETTINGS ==========
set APP_PKG=crypto_portable
set APP_ENTRY=%APP_PKG%.app
set VENV_DIR=.venv
set PYTHON=python

rem Required packages (GUI / data / HTTP / config)
set REQ_PKGS=pyarrow pandas duckdb polars pyside6 requests httpx pyyaml

rem Optional helpers executed when available
set TREEGEN=tools\treegen.py

rem ========== PATHS ==========
set BASE=%~dp0
set BASE=%BASE:~0,-1%
set PKG_DIR=%BASE%\%APP_PKG%
set SNAPSHOT=%BASE%\PORTABLE_TREE.txt

call :banner "Portable launcher (BASE = current folder)"

rem ---------------- [1] PYTHON ----------------
echo [1/9] Checking Python on PATH...
where %PYTHON% >nul 2>&1 || (
  echo ERROR: Python not found. Install Python 3.10+ and add it to PATH.
  goto :fail
)
for /f "delims=" %%v in ('%PYTHON% -c "import sys;print(sys.version.split()[0])"') do set PYV=%%v
echo   Python %PYV% found.
call :cont

rem ---------------- [2] LAYOUT ----------------
echo [2/9] Checking project layout...
if not exist "%PKG_DIR%\app.py" (
  echo ERROR: Package "%APP_PKG%" not found at: "%PKG_DIR%"
  echo Tip: place this BAT one level ABOVE the folder "crypto_portable".
  goto :fail
)
echo   Layout looks good.
call :cont

rem ---------------- [3] FOLDERS (under BASE) ----------------
echo [3/9] Ensuring folders under BASE...
for %%D in (config,library,library\raw,library\features,library\manifests,exports,logs) do (
  if not exist "%BASE%\%%D" mkdir "%BASE%\%%D"
)
echo   Folders are ready at: "%BASE%"
call :cont

rem ---------------- [4] CONFIG BOOTSTRAP ----------------
echo [4/9] Bootstrapping USDC config (idempotent)...
if exist "%BASE%\tools\bootstrap_usdc_config.py" (
  %PYTHON% "%BASE%\tools\bootstrap_usdc_config.py" >nul 2>&1 && (
    echo   Config ensured via bootstrap script.
  ) || (
    echo   WARNING: bootstrap script reported an issue (continuing).
  )
) else (
  echo   Bootstrap script not found, skipping.
)
call :cont

rem ---------------- [5] VENV ----------------
echo [5/9] Creating/activating virtual env: "%VENV_DIR%" ...
if not exist "%BASE%\%VENV_DIR%\Scripts\python.exe" (
  %PYTHON% -m venv "%BASE%\%VENV_DIR%" || (
    echo ERROR: Failed to create venv.
    goto :fail
  )
)
call "%BASE%\%VENV_DIR%\Scripts\activate.bat" || (
  echo ERROR: Failed to activate venv.
  goto :fail
)
echo   venv is active.
call :cont

rem ---------------- [6] DEPENDENCIES ----------------
echo [6/9] Making sure required packages are installed...
python -m pip install --upgrade pip >nul 2>&1 || (
  echo WARNING: pip upgrade failed, continuing with current version.
)
for %%P in (%REQ_PKGS%) do (
  python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('%%P') else 1)" >nul 2>&1
  if errorlevel 1 (
    echo   installing %%P ...
    pip install %%P || (
      echo ERROR: Failed to install %%P
      goto :fail
    )
  ) else (
    echo   %%P OK
  )
)
echo   All dependencies are present.
call :cont

rem ---------------- [7] INTEGRITY ----------------
echo [7/9] Deep integrity check (import package + write test)...
python -c "import importlib; importlib.import_module('%APP_PKG%')" || (
  echo ERROR: Cannot import package "%APP_PKG%".
  goto :fail
)
if not exist "%BASE%\library\_probe" mkdir "%BASE%\library\_probe"
echo ok> "%BASE%\library\_probe\touch.tmp" || (
  echo ERROR: Write permission test failed in library folder.
  goto :fail
)
del /q "%BASE%\library\_probe\touch.tmp" >nul 2>&1
echo   Integrity OK.
call :cont

rem ---------------- [8] TREE SNAPSHOT (safe, non-fatal) ----------------
echo [8/9] Generating folder tree snapshot (non-fatal)...
if exist "%BASE%\%TREEGEN%" (
  %PYTHON% "%BASE%\%TREEGEN%" "%BASE%\CryptoPortable" > "%SNAPSHOT%" 2>nul
  if errorlevel 1 (
    echo   WARNING: treegen run failed, falling back to TREE command.
    call :fallback_tree
  ) else (
    echo   Snapshot generated via treegen.
  )
) else (
  call :fallback_tree
)
call :cont

rem ---------------- [9] LAUNCH GUI ----------------
echo [9/9] Launching GUI with base dir:
echo   "%BASE%"
python -m %APP_ENTRY% --gui --base-dir "%BASE%"
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% NEQ 0 (
  echo GUI exited with code %EXITCODE%.
) else (
  echo GUI closed normally.
)
if "%PORTABLE_INTERACTIVE%"=="1" (
  echo All steps finished. Press any key to close...
  pause >nul
) else (
  echo All steps finished.
)
exit /b 0

rem ========== helpers ==========
:banner
echo -----------------------------------------------
echo %~1
echo -----------------------------------------------
exit /b 0

:cont
if "%PORTABLE_INTERACTIVE%"=="1" (
  echo   Step OK. Press any key to continue...
  pause >nul
) else (
  echo   Step OK.
)
exit /b 0

:fallback_tree
> "%SNAPSHOT%" echo %BASE%
tree "%BASE%" /F >> "%SNAPSHOT%" 2>nul
if errorlevel 1 (
  echo   WARNING: TREE command unavailable, snapshot skipped.
) else (
  echo   Snapshot generated via TREE command.
)
exit /b 0

:fail
if "%PORTABLE_INTERACTIVE%"=="1" (
  echo.
  echo Press any key to close...
  pause >nul
)
exit /b 1
