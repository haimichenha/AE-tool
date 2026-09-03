$ErrorActionPreference='Stop'
$log='C:\Users\Public\Documents\AE2022_final_clean.log'
try {
 $ae='D:\AZBao\PR 22\Ae2022\Adobe After Effects 2022'
 $config='C:\Users\chenha\AppData\Roaming\Adobe\After Effects\22.0'
 $backup='E:\插件备份\AE2022_退役备份_20260830'
 $targets=Get-Process -Name 'dynamiclinkmanager' -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$ae\Support Files\dynamiclinkmanager.exe" }
 foreach($p in $targets){ "Stopping: $($p.Id) $($p.Path)" | Add-Content -LiteralPath $log -Encoding utf8; Stop-Process -Id $p.Id -Force }
 Start-Sleep -Seconds 2
 if(Get-Process -Name 'dynamiclinkmanager' -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$ae\Support Files\dynamiclinkmanager.exe" }){throw 'AE2022 dynamiclinkmanager is still active'}
 if(Test-Path -LiteralPath $ae){Remove-Item -LiteralPath $ae -Recurse -Force -ErrorAction Stop; 'AE directory removed'|Add-Content -LiteralPath $log -Encoding utf8}
 if(Test-Path -LiteralPath $config){Remove-Item -LiteralPath $config -Recurse -Force -ErrorAction Stop; 'AE config removed'|Add-Content -LiteralPath $log -Encoding utf8}
 [pscustomobject]@{ae_path_exists=(Test-Path -LiteralPath $ae);config_exists=(Test-Path -LiteralPath $config);backup=$backup;completed_at=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $backup 'retirement_result.json') -Encoding utf8
 Get-Content -LiteralPath (Join-Path $backup 'retirement_result.json') -Raw | Add-Content -LiteralPath $log -Encoding utf8
 exit 0
} catch { $_ | Out-String | Add-Content -LiteralPath $log -Encoding utf8; exit 1 }
