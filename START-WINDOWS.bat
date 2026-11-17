@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  if not exist navbot\navbot.sqlite3 py -3 navbot\app.py --db navbot\navbot.sqlite3 --init-admin
  py -3 navbot\app.py --port 8081 --db navbot\navbot.sqlite3
) else (
  if not exist navbot\navbot.sqlite3 python navbot\app.py --db navbot\navbot.sqlite3 --init-admin
  python navbot\app.py --port 8081 --db navbot\navbot.sqlite3
)
pause
