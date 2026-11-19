param([string]$ConfigPath = (Join-Path $PSScriptRoot 'printer-config.json'),[switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Printing;
public static class NavbotReceiptPrinter {
  public static string DefaultName() { var p = new PrinterSettings(); return p.PrinterName; }
  public static bool Ready() {
    var p = new PrinterSettings();
      return p.IsValid && !System.Text.RegularExpressions.Regex.IsMatch(p.PrinterName, "PDF|XPS|OneNote|Fax", System.Text.RegularExpressions.RegexOptions.IgnoreCase);
  }
  public static void Print(string number, string university, string office, string section, string service, string stamp, string footer) {
    if(!Ready()) throw new InvalidOperationException("Physical default printer unavailable");
    using(var doc = new PrintDocument()) {
      doc.PrintController = new StandardPrintController();
      doc.DocumentName = "NAVBOT " + number;
      doc.PrinterSettings.PrintToFile = false;
      doc.DefaultPageSettings.PaperSize = new PaperSize("NAVBOT 80x70mm", 315, 276);
      doc.DefaultPageSettings.Margins = new Margins(0,0,0,0);
      doc.DefaultPageSettings.Landscape = false;
      doc.PrintPage += delegate(object sender, PrintPageEventArgs e) {
        var g=e.Graphics;g.PageUnit=GraphicsUnit.Millimeter;
        float y=2f,w=72f;
        using(var small=new Font("Arial",8f))
        using(var bold=new Font("Arial",8f,FontStyle.Bold))
        using(var large=new Font("Arial",28f,FontStyle.Bold))
        using(var center=new StringFormat()) {
          center.Alignment=StringAlignment.Center;center.LineAlignment=StringAlignment.Near;
          Action<string,Font,float> line=(text,font,maxHeight)=>{
            text=text??"";var size=g.MeasureString(text,font,new SizeF(w,maxHeight),center);
            float h=Math.Min(maxHeight,size.Height+0.7f);
            g.DrawString(text,font,Brushes.Black,new RectangleF(2f,y,w,h),center);y+=h+0.7f;
          };
          line(university,bold,11f);line(office,bold,5f);y+=1f;
          line(number,large,14f);y+=1f;line(section,small,7f);line(service,bold,8f);
          line(stamp,small,5f);line(footer,small,7f);
        }
        e.HasMorePages=false;
      };
      doc.Print(); // Windows spooler acknowledgement, not physical paper confirmation.
    }
  }
}
'@ -ReferencedAssemblies @('System.Drawing','System')
if($ValidateOnly){Write-Host 'Windows printer helper compilation: OK';Write-Host ('Default physical printer ready: '+[NavbotReceiptPrinter]::Ready());exit 0}
# One physical kiosk worker at a time. No localhost listener or browser extension.
$created=$false
$mutex=New-Object System.Threading.Mutex($true,'Global\NAVBOTReceiptPrinter',[ref]$created)
if(-not $created){$mutex.Dispose();exit 0}
try {
  $config=Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $server=[Uri]$config.server_url
  if($server.Scheme -notin @('http','https') -or $server.UserInfo -or $server.Query -or $server.Fragment -or $server.AbsolutePath -ne '/') {throw 'Invalid server URL'}
  if($config.token -notmatch '^[A-Za-z0-9_-]{40,128}$' -or $config.worker_id -notmatch '^[0-9a-f-]{36}$'){throw 'Invalid printer configuration'}
  # Keep credentials and the durable non-PII journal private to this Windows user.
  $folder=Join-Path $env:LOCALAPPDATA 'NavBoT\PrinterAgent'
  $null=New-Item -ItemType Directory -Path $folder -Force
  $identity=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
  & icacls.exe $folder /inheritance:r /grant:r "${identity}:(OI)(CI)F" | Out-Null
  if($LASTEXITCODE -ne 0){throw 'Cannot protect printer configuration'}
  & icacls.exe (Resolve-Path -LiteralPath $ConfigPath).Path /inheritance:r /grant:r "${identity}:F" | Out-Null
  if($LASTEXITCODE -ne 0){throw 'Cannot protect printer configuration'}
  $journalPath=Join-Path $folder 'print-journal.json'
  $journal=@{}
  if(Test-Path -LiteralPath $journalPath){$loaded=Get-Content -LiteralPath $journalPath -Raw -Encoding UTF8 | ConvertFrom-Json;foreach($property in $loaded.PSObject.Properties){$journal[$property.Name]=[string]$property.Value}}
  function Save-Journal {
    $temporary=$journalPath+'.tmp'
    [IO.File]::WriteAllText($temporary,($journal|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $journalPath -Force
  }
  function Send-Agent($data) {
    $data.worker_id=[string]$config.worker_id
    $json=$data|ConvertTo-Json -Depth 8 -Compress
    Invoke-RestMethod -Uri ($server.GetLeftPart([UriPartial]::Authority)+'/api/kiosk-printer/agent') -Method Post -Headers @{Authorization=('Bearer '+$config.token)} -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($json)) -TimeoutSec 15 -MaximumRedirection 0
  }
  while($true){
    try {
      $ready=[NavbotReceiptPrinter]::Ready()
      $response=Send-Agent @{action='poll';ready=$ready;printer_name=[NavbotReceiptPrinter]::DefaultName()}
      $job=$response.job
      if($null -ne $job){
        $key=([string]$job.ticket_id)+'_'+([string]$job.claim)
        if(-not $journal.ContainsKey($key) -and -not $job.fresh){$journal[$key]='uncertain';Save-Journal}
        if(-not $journal.ContainsKey($key)){
          $journal[$key]='attempting';Save-Journal # Persist BEFORE the irreversible print call.
          try {
            $r=$job.receipt
            $stamp=[DateTimeOffset]::Parse([string]$r.created_at).ToOffset([TimeSpan]::FromHours(5)).ToString('dd.MM.yyyy HH:mm')
            [NavbotReceiptPrinter]::Print([string]$r.number,[string]$r.university,[string]$r.office,[string]$r.section,[string]$r.service,$stamp,[string]$r.footer)
            $journal[$key]='spooled'
          } catch {$journal[$key]='failed'}
          Save-Journal
        }
        $state=$journal[$key]
        if($state -eq 'attempting'){$state='uncertain';$journal[$key]=$state;Save-Journal}
        $null=Send-Agent @{action='ack';ticket_id=[long]$job.ticket_id;claim=[string]$job.claim;state=$state}
      }
    } catch {
      # No payloads, credentials or raw network exceptions are written to logs.
      Start-Sleep -Seconds 3
    }
    Start-Sleep -Milliseconds 700
  }
} finally {$mutex.ReleaseMutex();$mutex.Dispose()}
