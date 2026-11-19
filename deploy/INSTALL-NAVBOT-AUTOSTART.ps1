param([switch]$Remove,[switch]$ValidateOnly)
$ErrorActionPreference='Stop'
if($ValidateOnly){
  foreach($file in @('START-NAVBOT-NATIVE.ps1','INSTALL-NAVBOT-AUTOSTART.ps1','NAVBOT-PRINT-AGENT.ps1')){
    $tokens=$null;$errors=$null
    $null=[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $file),[ref]$tokens,[ref]$errors)
    if($errors.Count){throw ('PowerShell syntax error: '+$file)}
  }
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'NAVBOT-PRINT-AGENT.ps1') -ValidateOnly
  if($LASTEXITCODE -ne 0){throw 'Printer helper validation failed'}
  Write-Host 'Windows startup scripts: OK. No tasks or settings were changed.'
  exit 0
}
$identity=[System.Security.Principal.WindowsIdentity]::GetCurrent()
$sid=$identity.User.Value
$name='NAVBOT-Kiosk-'+$sid
$install=Join-Path $env:LOCALAPPDATA 'NavBoT\NativeKiosk'
$statePath=Join-Path $install 'autostart-state.json'
$winlogon='HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Winlogon'
$scheduler=New-Object -ComObject Schedule.Service
$scheduler.Connect()
$folder=$scheduler.GetFolder('\')
try {$oldTask=$folder.GetTask($name)}catch{$oldTask=$null}
if($oldTask -and $oldTask.Definition.RegistrationInfo.Source -ne 'NAVBOT'){throw 'Task name is used by another application'}
if($Remove){
  if($oldTask){$folder.DeleteTask($name,0)}
  if(Test-Path -LiteralPath $statePath){
    $state=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8|ConvertFrom-Json
    if($state.sid -ne $sid){throw 'Wrong kiosk user'}
    # Restore only a value still equal to the setting this installer wrote.
    $current=(Get-ItemProperty -LiteralPath $winlogon -Name RestartApps -ErrorAction SilentlyContinue).RestartApps
    if($current -eq 0){if($state.restartExisted){Set-ItemProperty -LiteralPath $winlogon -Name RestartApps -Value ([int]$state.restartValue)}else{Remove-ItemProperty -LiteralPath $winlogon -Name RestartApps -ErrorAction SilentlyContinue}}
    foreach($item in $state.startupItems){if((Test-Path -LiteralPath $item.backup) -and -not(Test-Path -LiteralPath $item.original)){Move-Item -LiteralPath $item.backup -Destination $item.original}}
    Remove-Item -LiteralPath $statePath
  }
  Write-Host 'NAVBOT avtomatik ishga tushishi bekor qilindi. Asosiy fayllar saqlangan.'
  exit 0
}
$null=New-Item -ItemType Directory -Path $install -Force
& icacls.exe $install /inheritance:r /grant:r ($identity.Name+':(OI)(CI)F')|Out-Null
if($LASTEXITCODE -ne 0){throw 'Cannot protect kiosk configuration folder'}
$configSource=Join-Path $PSScriptRoot 'printer-config.json'
$configTarget=Join-Path $install 'printer-config.json'
if(-not(Test-Path -LiteralPath $configSource)){if(Test-Path -LiteralPath $configTarget){$configSource=$configTarget}else{throw 'printer-config.json must be beside the installer'}}
# Validate without displaying or passing the token on a command line.
try{$config=Get-Content -LiteralPath $configSource -Raw -Encoding UTF8|ConvertFrom-Json}catch{throw 'Cannot read printer-config.json'}
$uri=[Uri]$config.server_url
if($uri.Scheme -notin @('http','https') -or $uri.UserInfo -or $uri.Query -or $uri.Fragment -or $uri.AbsolutePath -ne '/' -or $config.token -notmatch '^[A-Za-z0-9_-]{40,128}$'){throw 'Invalid printer-config.json'}
$files=@('START-NAVBOT-NATIVE.ps1','NAVBOT-PRINT-AGENT.ps1','NAVBOT-START.html')
foreach($file in $files){$source=Join-Path $PSScriptRoot $file;$target=Join-Path $install $file;if(-not(Test-Path -LiteralPath $source)){throw ('Missing '+$file)};if([IO.Path]::GetFullPath($source) -ne [IO.Path]::GetFullPath($target)){Copy-Item -LiteralPath $source -Destination $target -Force}}
if([IO.Path]::GetFullPath($configSource) -ne [IO.Path]::GetFullPath($configTarget)){Copy-Item -LiteralPath $configSource -Destination $configTarget -Force}
$prior=Get-ItemProperty -LiteralPath $winlogon -Name RestartApps -ErrorAction SilentlyContinue
$state=@{sid=$sid;restartExisted=($null -ne $prior);restartValue=0;startupItems=@()}
if($null -ne $prior){$state.restartValue=[int]$prior.RestartApps}
if(Test-Path -LiteralPath $statePath){$state=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8|ConvertFrom-Json;if($state.sid -ne $sid){throw 'Wrong kiosk user'}}
function Save-State {[IO.File]::WriteAllText($statePath,($state|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))}
Save-State
# Register a per-user interactive logon task. No password, elevation, Explorer
# shell replacement, global startup delay setting or automatic reboot is used.
$task=$scheduler.NewTask(0)
$task.RegistrationInfo.Source='NAVBOT'
$task.RegistrationInfo.Description='NAVBOT kiosk and printer helper at this user logon'
$task.Principal.UserId=$sid;$task.Principal.LogonType=3;$task.Principal.RunLevel=0
$task.Settings.Enabled=$true;$task.Settings.StartWhenAvailable=$true
$task.Settings.DisallowStartIfOnBatteries=$false;$task.Settings.StopIfGoingOnBatteries=$false
$task.Settings.ExecutionTimeLimit='PT0S';$task.Settings.MultipleInstances=2
$trigger=$task.Triggers.Create(9);$trigger.UserId=$sid;$trigger.Delay='PT0S';$trigger.Enabled=$true
$action=$task.Actions.Create(0)
$action.Path=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$action.Arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+(Join-Path $install 'START-NAVBOT-NATIVE.ps1')+'" -Unattended'
$action.WorkingDirectory=$install
$null=$folder.RegisterTaskDefinition($name,$task,6,$sid,$null,3)
# Preserve and remove only identifiable old NAVBOT startup entries.
$startup=[Environment]::GetFolderPath('Startup')
$backup=Join-Path $install 'old-startup'
$null=New-Item -ItemType Directory -Path $backup -Force
$shell=New-Object -ComObject WScript.Shell
foreach($item in Get-ChildItem -LiteralPath $startup -File){
  $ours=$false
  if($item.Extension -eq '.lnk'){
    $link=$shell.CreateShortcut($item.FullName)
    $leaf=[IO.Path]::GetFileName($link.TargetPath)
    $ours=$leaf -in @('START-NAVBOT-NATIVE.bat','START-NAVBOT-NATIVE.ps1','printer-config.json')
  }elseif($item.Name -eq 'printer-config.json'){$ours=$true
  }elseif($item.Extension -eq '.bat'){
    $text=Get-Content -LiteralPath $item.FullName -Raw
    $ours=$text -match 'START-NAVBOT-NATIVE\.ps1|NAVBOT-PRINT-AGENT\.ps1'
  }
  if($ours){$target=Join-Path $backup (([Guid]::NewGuid().ToString())+'-'+$item.Name);$state.startupItems+=@{original=$item.FullName;backup=$target};Save-State;Move-Item -LiteralPath $item.FullName -Destination $target}
}
# Stop Windows from restoring an editor with printer-config.json on next logon.
$null=New-Item -Path $winlogon -Force
$null=New-ItemProperty -LiteralPath $winlogon -Name RestartApps -Value 0 -PropertyType DWord -Force
Save-State
Write-Host 'Tayyor. Keyingi Windows hisobiga kirishda kiosk kechikishsiz boshlanadi.'
Write-Host 'Windows login/paroli ozgartirilmadi. JSON faylni alohida ochish kerak emas.'
