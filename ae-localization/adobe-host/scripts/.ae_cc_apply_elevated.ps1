$ErrorActionPreference='Stop'
$log='C:\Users\Public\Documents\AE_CC_apply.log'
try {
  "Started: $(Get-Date -Format o)" | Set-Content -LiteralPath $log -Encoding utf8
  $active=Get-Process -Name 'AfterFX','Adobe Premiere Pro' -ErrorAction SilentlyContinue
  if($active){ throw "Adobe host is running: $($active.ProcessName -join ', ')" }
  $env:PYTHONUTF8='1'
  & 'C:\Python313\python.exe' (Join-Path $PSScriptRoot '.ae_cc_effect_localize.py') --apply *>&1 | Out-File -LiteralPath $log -Append -Encoding utf8
  "ExitCode: $LASTEXITCODE" | Add-Content -LiteralPath $log -Encoding utf8
  exit $LASTEXITCODE
} catch { "ERROR: $($_ | Out-String)" | Add-Content -LiteralPath $log -Encoding utf8; exit 1 }
