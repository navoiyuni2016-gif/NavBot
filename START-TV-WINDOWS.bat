@echo off
setlocal
cd /d "%~dp0"
set "NAVBOT_CHROME="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "NAVBOT_CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined NAVBOT_CHROME if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "NAVBOT_CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined NAVBOT_CHROME if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "NAVBOT_CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if not defined NAVBOT_CHROME (
  echo Google Chrome topilmadi. Avval Google Chrome o'rnating.
  pause
  exit /b 1
)
echo NavBoT serveri tekshirilmoqda...
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://127.0.0.1:8081/api/catalog; if($r.StatusCode -eq 200){exit 0} } catch {}; exit 1"
if errorlevel 1 start "NavBoT server" cmd /c call "%~dp0START-WINDOWS.bat"
powershell -NoProfile -Command "for($i=0;$i -lt 30;$i++){try{$r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 http://127.0.0.1:8081/api/catalog;if($r.StatusCode -eq 200){exit 0}}catch{};Start-Sleep -Milliseconds 500};exit 1"
if errorlevel 1 (
  echo Server ishga tushmadi. NavBoT server oynasidagi xatoni tekshiring.
  pause
  exit /b 1
)
echo TV ovozi avtomatik yoqilgan. Windows ovoz darajasini tekshiring.
start "NavBoT TV" "%NAVBOT_CHROME%" --user-data-dir="%LOCALAPPDATA%\NavBoT\ChromeTV" --no-first-run --no-default-browser-check --autoplay-policy=no-user-gesture-required --kiosk "http://127.0.0.1:8081/tv"
endlocal
