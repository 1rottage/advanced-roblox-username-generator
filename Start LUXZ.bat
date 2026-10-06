@echo off
cd /d "%~dp0"
title LUXZ Launcher

echo Installing or checking LUXZ requirements...
python -m pip install -r requirements.txt
if errorlevel 1 goto install_failed

echo.
echo Starting LUXZ...
python luxz.py
if errorlevel 1 goto app_failed

echo.
echo LUXZ has closed.
pause
exit /b 0

:install_failed
echo.
echo Could not install the required packages. Check your internet connection and Python installation.
pause
exit /b 1

:app_failed
echo.
echo LUXZ stopped because of an error. The message is shown above.
pause
exit /b 1
