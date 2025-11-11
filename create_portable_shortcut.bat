@echo off
setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "LNK=%USERPROFILE%\Desktop\CryptoPortable.lnk"
set "TARGET=%ROOT%\run_portable.bat"
set "ICON=%ROOT%\icons\crypto.ico"

if not exist "%TARGET%" (
  echo Launcher not found: %TARGET%
  pause
  exit /b 1
)

powershell -NoProfile -Command ^
  "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%LNK%');" ^
  "$s.TargetPath='%TARGET%'; $s.WorkingDirectory='%ROOT%';" ^
  "if (Test-Path '%ICON%') { $s.IconLocation='%ICON%'; }" ^
  "$s.Save()"

if exist "%ICON%" (
  echo Shortcut created: %LNK% (icon applied)
) else (
  echo Shortcut created: %LNK%
  echo Tip: place a custom icon at %ICON% to personalize the shortcut.
)

pause
