$ErrorActionPreference='Stop'
$log='C:\Users\Public\Documents\Universe_dashboard_cn_clone.log'
try {
  "Started: $(Get-Date -Format o)" | Set-Content -LiteralPath $log -Encoding utf8
  $env:PYTHONUTF8='1'
  & 'C:\Python313\python.exe' (Join-Path $PSScriptRoot '.create_universe_dashboard_cn.py') --apply *>&1 | Out-File -LiteralPath $log -Append -Encoding utf8
  "ExitCode: $LASTEXITCODE" | Add-Content -LiteralPath $log -Encoding utf8
  exit $LASTEXITCODE
} catch { "ERROR: $($_ | Out-String)" | Add-Content -LiteralPath $log -Encoding utf8; exit 1 }
