$ErrorActionPreference='Stop'
$root='C:\Program Files\Adobe\Common\Plug-ins\7.0\MediaCore'
$sourceRoot='E:\插件备份\AE_PR_汉化工作\Universe_试验回滚前快照_20260830'
$work='E:\插件备份\AE_PR_汉化工作'
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
 $source=Join-Path $sourceRoot $rel; $target=Join-Path $root $rel
 if(!(Test-Path -LiteralPath $source) -or !(Test-Path -LiteralPath $target)){throw "Missing Chinese snapshot or target: $rel"}
 $expected=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
 Copy-Item -LiteralPath $source -Destination $target -Force
 $actual=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
 if($actual -ne $expected){throw "Hash verification failed: $rel"}
 $result += [pscustomobject]@{file=$rel;source_sha=$expected;target_sha=$actual}
}
$result | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $work 'Universe_全中文模式_切换清单_20260830.json') -Encoding utf8
[pscustomobject]@{mode='full_chinese_display';changed_at=(Get-Date -Format o);files=$files;dashboard='unsupported: original effect-name lookup is changed'} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $work 'Universe_当前模式.json') -Encoding utf8
"Applied full-Chinese Universe profile: $($result.Count)/$($files.Count) pilot files re-localized."
