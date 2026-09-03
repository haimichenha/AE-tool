$ErrorActionPreference='Stop'
$ae='D:\AZBao\PR 22\Ae2022\Adobe After Effects 2022'
$config='C:\Users\chenha\AppData\Roaming\Adobe\After Effects\22.0'
$backup='E:\插件备份\AE2022_退役备份_20260830'
$active=Get-Process -Name 'AfterFX','Adobe Premiere Pro' -ErrorAction SilentlyContinue
if($active){throw "Adobe host is running: $($active.ProcessName -join ', ')"}
if(!(Test-Path -LiteralPath $backup)){throw 'Required backup is missing'}
& reg.exe export 'HKCU\SOFTWARE\Adobe\After Effects\22.0' (Join-Path $backup 'AE22_UserRegistry.reg') /y 2>$null
foreach($path in @($ae,$config)){
 if(Test-Path -LiteralPath $path){
  $resolved=(Resolve-Path -LiteralPath $path).Path
  if($resolved -ne $path){throw "Resolved path mismatch: $resolved"}
  Remove-Item -LiteralPath $path -Recurse -Force
 }
}
$uninstallRoots=@('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall')
$removedKeys=@()
foreach($root in $uninstallRoots){
 if(Test-Path -LiteralPath $root){
  Get-ChildItem -LiteralPath $root | ForEach-Object {
   $prop=Get-ItemProperty -LiteralPath $_.PSPath -ErrorAction SilentlyContinue
   if($prop.DisplayName -eq 'Adobe After Effects 2022'){
    $removedKeys += $_.PSPath
    Remove-Item -LiteralPath $_.PSPath -Recurse -Force
   }
  }
 }
}
$result=[pscustomobject]@{ae_path_exists=(Test-Path -LiteralPath $ae);config_exists=(Test-Path -LiteralPath $config);backup=$backup;uninstall_keys_removed=$removedKeys;completed_at=(Get-Date -Format o)}
$result|ConvertTo-Json -Depth 3|Set-Content -LiteralPath (Join-Path $backup 'retirement_result.json') -Encoding utf8
$result|ConvertTo-Json -Depth 3
