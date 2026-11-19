@echo off
setlocal
rem Standalone launcher for the existing NAVBOT server. Does not start a local database.
if not defined NAVBOT_KIOSK_URL set "NAVBOT_KIOSK_URL=http://172.20.30.31/kiosk"
if not "%~1"=="" set "NAVBOT_KIOSK_URL=%~1"
set "NAVBOT_KIOSK_CHROME="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "NAVBOT_KIOSK_CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined NAVBOT_KIOSK_CHROME if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "NAVBOT_KIOSK_CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined NAVBOT_KIOSK_CHROME if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "NAVBOT_KIOSK_CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if not defined NAVBOT_KIOSK_CHROME (
  echo Google Chrome topilmadi. Avval Google Chrome o'rnating.
  pause
  exit /b 1
)
powershell -NoProfile -Command "try {$u=[Uri]$env:NAVBOT_KIOSK_URL; if($u.Scheme -notin @('http','https') -or $u.AbsolutePath -ne '/kiosk' -or $u.UserInfo -or $u.Query -or $u.Fragment){exit 1}; $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 ($u.GetLeftPart([System.UriPartial]::Authority)+'/api/catalog'); if($r.StatusCode -eq 200){exit 0}}catch{};exit 1"
if errorlevel 1 (
  echo Serverga ulanmadi. LAN yoki internet manzilini va tarmoqni tekshiring.
  pause
  exit /b 1
)
echo Oldingi kiosk oynalarini Alt+F4 bilan yoping.
echo 80 mm chek printeri Windows DEFAULT printeri bo'lishi kerak.
echo Kioskni yopish: Alt+F4.
start "NAVBOT Kiosk" "%NAVBOT_KIOSK_CHROME%" --user-data-dir="%LOCALAPPDATA%\NavBoT\ChromeKioskLAN" --no-first-run --no-default-browser-check --disable-session-crashed-bubble --kiosk-printing --kiosk "%NAVBOT_KIOSK_URL%"
endlocal
