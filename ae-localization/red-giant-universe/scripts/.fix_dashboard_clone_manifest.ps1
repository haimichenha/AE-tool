$ErrorActionPreference='Stop'
$log='C:\Users\Public\Documents\fix_dashboard_clone_manifest.log'
try {
 $manifest='C:\Program Files (x86)\Common Files\Adobe\CEP\extensions\com.redgiant.uni.dashboard.cn\CSXS\manifest.xml'
 $raw=Get-Content -LiteralPath $manifest -Raw
 if($raw -notmatch 'com\.redgiant\.uni\.dashboard\.cn\.cn\.extension'){throw 'Expected malformed clone ID not found'}
 $raw=$raw.Replace('com.redgiant.uni.dashboard.cn.cn.extension','com.redgiant.uni.dashboard.cn.extension')
 Set-Content -LiteralPath $manifest -Value $raw -Encoding utf8
 Select-String -LiteralPath $manifest -Pattern '<Extension Id=' | ForEach-Object Line | Set-Content -LiteralPath $log -Encoding utf8
 exit 0
} catch { $_ | Out-String | Set-Content -LiteralPath $log -Encoding utf8; exit 1 }
