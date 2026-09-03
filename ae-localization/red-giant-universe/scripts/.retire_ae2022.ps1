$ErrorActionPreference='Stop'
$ae='D:\AZBao\PR 22\Ae2022\Adobe After Effects 2022'
$config='C:\Users\chenha\AppData\Roaming\Adobe\After Effects\22.0'
$backup='E:\插件备份\AE2022_退役备份_20260830'
$uninstaller='C:\Program Files (x86)\Common Files\Adobe\Adobe Desktop Common\HDBox\Uninstaller.exe'
$args=@('--uninstall=1','--sapCode=AEFT','--productVersion=22.0','--productPlatform=win64','--productAdobeCode={AEFT-22.0-64-ADBEADBEADBEADBEADBEADBE}','--productName=After Effects','--mode=1')
$active=Get-Process -Name 'AfterFX','Adobe Premiere Pro' -ErrorAction SilentlyContinue
if($active){throw "Adobe host is running: $($active.ProcessName -join ', ')"}
if(!(Test-Path -LiteralPath $ae)){throw "AE 2022 path missing: $ae"}
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$scriptSource=Join-Path $ae 'Support Files\Scripts'
if(Test-Path -LiteralPath $scriptSource){Copy-Item -LiteralPath $scriptSource -Destination (Join-Path $backup 'Support Files') -Recurse -Force}
if(Test-Path -LiteralPath $config){Copy-Item -LiteralPath $config -Destination (Join-Path $backup 'UserConfig') -Recurse -Force}
[pscustomobject]@{ae_path=$ae;config_path=$config;uninstaller=$uninstaller;uninstall_arguments=$args;backup=$backup;backed_up_at=(Get-Date -Format o)} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $backup 'retirement_manifest.json') -Encoding utf8
if(Test-Path -LiteralPath $uninstaller){$p=Start-Process -FilePath $uninstaller -ArgumentList $args -PassThru -Wait -WindowStyle Normal; "Official uninstaller exit code: $($p.ExitCode)"}else{"Official uninstaller not found; using post-backup file cleanup."}
if(Test-Path -LiteralPath $ae){
  $resolved=(Resolve-Path -LiteralPath $ae).Path
  if($resolved -ne $ae){throw "Resolved AE path mismatch: $resolved"}
  Remove-Item -LiteralPath $ae -Recurse -Force
}
if(Test-Path -LiteralPath $config){
  $resolved=(Resolve-Path -LiteralPath $config).Path
  if($resolved -ne $config){throw "Resolved config path mismatch: $resolved"}
  Remove-Item -LiteralPath $config -Recurse -Force
}
[pscustomobject]@{ae_path_exists=(Test-Path -LiteralPath $ae);config_exists=(Test-Path -LiteralPath $config);backup_exists=(Test-Path -LiteralPath $backup);completed_at=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $backup 'retirement_result.json') -Encoding utf8
Get-Content -LiteralPath (Join-Path $backup 'retirement_result.json') -Raw
