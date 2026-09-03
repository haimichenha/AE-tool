$ErrorActionPreference='Stop'
$log='C:\Users\Public\Documents\AE2022_force_clean_diagnostic.log'
try {
 $ae='D:\AZBao\PR 22\Ae2022\Adobe After Effects 2022'
 $config='C:\Users\chenha\AppData\Roaming\Adobe\After Effects\22.0'
 "AE exists before: $(Test-Path -LiteralPath $ae)" | Set-Content -LiteralPath $log -Encoding utf8
 "Config exists before: $(Test-Path -LiteralPath $config)" | Add-Content -LiteralPath $log -Encoding utf8
 if(Test-Path -LiteralPath $ae){ Remove-Item -LiteralPath $ae -Recurse -Force -ErrorAction Stop; 'AE directory removed' | Add-Content -LiteralPath $log -Encoding utf8 }
 if(Test-Path -LiteralPath $config){ Remove-Item -LiteralPath $config -Recurse -Force -ErrorAction Stop; 'Config directory removed' | Add-Content -LiteralPath $log -Encoding utf8 }
 "AE exists after: $(Test-Path -LiteralPath $ae)" | Add-Content -LiteralPath $log -Encoding utf8
 "Config exists after: $(Test-Path -LiteralPath $config)" | Add-Content -LiteralPath $log -Encoding utf8
 exit 0
} catch { $_ | Out-String | Add-Content -LiteralPath $log -Encoding utf8; exit 1 }
