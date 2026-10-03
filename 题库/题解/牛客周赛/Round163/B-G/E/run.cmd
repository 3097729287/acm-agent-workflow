@echo off
chcp 65001 >nul
cd /d "%~dp0"
python cross_visual.py
echo.
echo ================================================================
echo Done. Press any key to close this window.
pause >nul
