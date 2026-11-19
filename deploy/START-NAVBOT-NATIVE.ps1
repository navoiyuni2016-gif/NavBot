param([switch]$Unattended)
$ErrorActionPreference='Stop'
$mutex=$null;$owned=$false
try {
  $mutex=New-Object System.Threading.Mutex($true,'Global\NAVBOTKioskStartup',[ref]$owned)
  if(-not $owned){exit 0}
  $configPath=Join-Path $PSScriptRoot 'printer-config.json'
  $config=Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $server=[Uri]$config.server_url
  if($server.Scheme -notin @('http','https') -or $server.UserInfo -or $server.Query -or $server.Fragment -or $server.AbsolutePath -ne '/') {throw 'Invalid server address'}
  $chrome=$null
  foreach($root in @($env:ProgramFiles,${env:ProgramFiles(x86)},$env:LOCALAPPDATA)) {
    if($root){$candidate=Join-Path $root 'Google\Chrome\Application\chrome.exe';if(Test-Path -LiteralPath $candidate){$chrome=$candidate;break}}
  }
  if(-not $chrome){throw 'Google Chrome not installed'}
  $readyPath=Join-Path $PSScriptRoot 'startup-ready.js'
  [IO.File]::WriteAllText($readyPath,'window.navbotKioskUrl="";',[Text.UTF8Encoding]::new($false))
  $splash=Join-Path $PSScriptRoot 'NAVBOT-START.html'
  if(-not(Test-Path -LiteralPath $splash)){throw 'Missing NAVBOT-START.html'}
  $splashUrl=([Uri]$splash).AbsoluteUri
  $profile=Join-Path $env:LOCALAPPDATA 'NavBoT\ChromeNativePrinter'
  # Show the kiosk immediately; do not wait for the printer compiler or a timer.
  Start-Process -FilePath $chrome -ArgumentList @(('--user-data-dir="'+$profile+'"'),'--no-first-run','--no-default-browser-check','--kiosk-printing','--kiosk',('"'+$splashUrl+'"'))
  $agent=Join-Path $PSScriptRoot 'NAVBOT-PRINT-AGENT.ps1'
  Start-Process -FilePath 'powershell.exe' -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$agent+'" -ConfigPath "'+$configPath+'"')
  $origin=$server.GetLeftPart([UriPartial]::Authority)
  while($true){
    try {
      $response=Invoke-WebRequest -UseBasicParsing -Uri ($origin+'/api/catalog') -TimeoutSec 2 -MaximumRedirection 0
      if($response.StatusCode -eq 200){break}
    } catch {}
    Start-Sleep -Milliseconds 500
  }
  # Only the public kiosk URL goes into this browser-readable file, never the key.
  $target=($origin+'/kiosk')|ConvertTo-Json -Compress
  [IO.File]::WriteAllText($readyPath,('window.navbotKioskUrl='+$target+';'),[Text.UTF8Encoding]::new($false))
} catch {
  $message='Konfiguratsiya yoki Google Chrome topilmadi. printer-config.json faylini tekshiring.'
  try{[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'startup-status.txt'),$message,[Text.UTF8Encoding]::new($false))}catch{}
  if(-not $Unattended){Write-Host $message;Read-Host 'Yopish uchun Enter'}
  exit 1
} finally {if($null -ne $mutex){if($owned){$mutex.ReleaseMutex()};$mutex.Dispose()}}
