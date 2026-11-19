@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL-NAVBOT-AUTOSTART.ps1" -Remove
pause
