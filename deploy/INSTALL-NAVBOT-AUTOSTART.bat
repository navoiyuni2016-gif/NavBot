@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL-NAVBOT-AUTOSTART.ps1"
if errorlevel 1 echo OrnatiImadi. Yuqoridagi xato va printer-config.json faylini tekshiring.
pause
