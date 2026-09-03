$ErrorActionPreference = 'Stop'
$log = 'C:\Users\Public\Documents\AE_PR_apply.log'
try {
  "Started: $(Get-Date -Format o)" | Set-Content -LiteralPath $log -Encoding utf8
  "Identity: $(whoami)" | Add-Content -LiteralPath $log -Encoding utf8
  $source = Get-ChildItem -LiteralPath 'E:\' -Recurse -File -Filter 'localize_effect_browser.py' | Select-Object -First 1
  if ($null -eq $source) { throw 'Localization script was not found on E drive.' }
  "Script: $($source.FullName)" | Add-Content -LiteralPath $log -Encoding utf8
  $env:PYTHONUTF8 = '1'
  & 'C:\Python313\python.exe' $source.FullName --apply *>&1 | Out-File -LiteralPath $log -Append -Encoding utf8
  "ExitCode: $LASTEXITCODE" | Add-Content -LiteralPath $log -Encoding utf8
  exit $LASTEXITCODE
} catch {
  "ERROR: $($_ | Out-String)" | Add-Content -LiteralPath $log -Encoding utf8
  exit 1
}
