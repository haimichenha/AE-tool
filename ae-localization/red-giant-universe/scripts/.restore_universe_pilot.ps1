$ErrorActionPreference='Stop'
$root='C:\Program Files\Adobe\Common\Plug-ins\7.0\MediaCore'
$baseline='E:\插件备份\AE_PR_汉化工作\MediaCore_汉化前备份_20260830'
$snapshot='E:\插件备份\AE_PR_汉化工作\Universe_试验回滚前快照_20260830'
$manifest='E:\插件备份\AE_PR_汉化工作\Universe_试验恢复清单_20260830.json'
$files=@(
 'Red Giant Universe\Universe_Transitions_Cube_AE_Fx.aex',
 'Red Giant Universe\Universe_Transitions_Carousel_Transition_AE_Fx.aex',
 'Red Giant Universe\Universe_Utilities_Socialize_AE_Fx.aex',
 'Red Giant Universe\Universe_Transitions_Camera_Shake_Transition_AE_Fx.aex',
 'Red Giant Universe\Universe_Transitions_Color_Mosaic_AE_Fx.aex'
)
$active=Get-Process -Name 'AfterFX','Adobe Premiere Pro' -ErrorAction SilentlyContinue
if($active){throw "Adobe host is running: $($active.ProcessName -join ', ')"}
$result=@()
foreach($rel in $files){
  $target=Join-Path $root $rel; $source=Join-Path $baseline $rel; $snap=Join-Path $snapshot $rel
  if(!(Test-Path -LiteralPath $target) -or !(Test-Path -LiteralPath $source)){throw "Missing target or baseline: $rel"}
  $snapDir=Split-Path -Parent $snap; New-Item -ItemType Directory -Path $snapDir -Force | Out-Null
  if(!(Test-Path -LiteralPath $snap)){Copy-Item -LiteralPath $target -Destination $snap -Force}
  $before=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  $expected=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
  Copy-Item -LiteralPath $source -Destination $target -Force
  $after=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  if($after -ne $expected){throw "Hash verification failed: $rel"}
  $result += [pscustomobject]@{file=$rel;sha_before=$before;sha_after=$after;baseline_sha=$expected;snapshot=$snap}
}
$result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifest -Encoding utf8
"Restored pilot files: $($result.Count)"
$result | ForEach-Object { "$($_.file) | verified=$($_.sha_after -eq $_.baseline_sha)" }
