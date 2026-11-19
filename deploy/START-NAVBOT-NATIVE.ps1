$ErrorActionPreference='Stop'
try {
  $configPath=Join-Path $PSScriptRoot 'printer-config.json'
  $config=Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $server=[Uri]$config.server_url
  if($server.Scheme -notin @('http','https') -or $server.UserInfo -or $server.Query -or $server.Fragment -or $server.AbsolutePath -ne '/') {throw 'Invalid server address'}
  $chrome=$null
  foreach($root in @($env:ProgramFiles,${env:ProgramFiles(x86)},$env:LOCALAPPDATA)) {
    if($root){$candidate=Join-Path $root 'Google\Chrome\Application\chrome.exe';if(Test-Path -LiteralPath $candidate){$chrome=$candidate;break}}
  }
  if(-not $chrome){throw 'Google Chrome not installed'}
  $agent=Join-Path $PSScriptRoot 'NAVBOT-PRINT-AGENT.ps1'
  Start-Process -FilePath 'powershell.exe' -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$agent+'" -ConfigPath "'+$configPath+'"')
  Start-Sleep -Seconds 3
  $profile=Join-Path $env:LOCALAPPDATA 'NavBoT\ChromeNativePrinter'
  Start-Process -FilePath $chrome -ArgumentList @(('--user-data-dir="'+$profile+'"'),'--no-first-run','--no-default-browser-check','--kiosk-printing','--kiosk',('"'+$server.GetLeftPart([UriPartial]::Authority)+'/kiosk"'))
} catch {
  Write-Host 'Konfiguratsiya yoki Google Chrome topilmadi. printer-config.json faylini shu papkaga qoying.'
  Read-Host 'Yopish uchun Enter'
  exit 1
}
