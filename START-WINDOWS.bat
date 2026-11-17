@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 navbot\app.py --port 8081 --db navbot\navbot.sqlite3 --seed-demo
) else (
  python navbot\app.py --port 8081 --db navbot\navbot.sqlite3 --seed-demo
)
pause
