[CmdletBinding()]
param(
 [string]$Candidate='D:\tmp\lighting-localization-20260910\candidate\T_Glare.aex',
 [string]$HostRoot='D:\AZBao\PR 22\Ae2022\Adobe After Effects 2025\Support Files',
 [string]$Report='D:\tmp\lighting-localization-20260910\deployment.json'
)
$ErrorActionPreference='Stop'
$expectedAex='22EC5D28D61B32170400AB7BBD764D47E920F68C76141D2AB21849DBAB87EBA6'
$expectedCore='7F077A162E7DF5A264A05D10BA5BB6D1AC3B9E40647E66EB0D0EF4D2FB82F223'
$runtime='D:\tmp\saprt\glare01'
$mocha='D:\tmp\saprt\l3dao\lib64\BorisFX.Sapphire.mocha.em64t\mocha4bcc.dll'
$running=Get-Process | Where-Object {$_.ProcessName -match '^(AfterFX|Adobe Premiere Pro|AdobePremierePro|mocha.*)$'}
if ($running) {throw 'Close AE/Premiere/Mocha before installation; no process will be killed.'}
$hostFull=[IO.Path]::GetFullPath($HostRoot)
if (-not (Test-Path -LiteralPath (Join-Path $hostFull 'AfterFX.exe'))) {throw 'AE host identity missing'}
$dest=[IO.Path]::GetFullPath((Join-Path $hostFull 'Plug-ins\Effects\Sapphire Patch Lab\T_Glare.aex'))
if (-not $dest.StartsWith($hostFull+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'Destination escaped host directory'}
if (Test-Path -LiteralPath $dest) {throw 'Existing test entry will not be overwritten'}
if (Test-Path -LiteralPath $Report) {throw 'Existing deployment report will not be overwritten'}
if ((Get-FileHash -LiteralPath $Candidate).Hash -ne $expectedAex) {throw 'Candidate AEX hash mismatch'}
if ((Get-FileHash -LiteralPath (Join-Path $runtime 'lib64\sapphire_ae.dll')).Hash -ne $expectedCore) {throw 'Runtime core hash mismatch'}
if ((Get-FileHash -LiteralPath $mocha).Hash -ne '9141D09D02DD2E303E2BDB6F5BAB21844A441201562A5CE85790489FD0020030') {throw 'Localized Mocha dependency changed'}
$manifest=Get-Content -LiteralPath (Join-Path $runtime 'runtime-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($entry in $manifest.files) {
 $file=[IO.Path]::GetFullPath((Join-Path $runtime $entry.relative_path))
 if (-not $file.StartsWith($runtime+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Runtime manifest escaped root'}
 if ((Get-FileHash -LiteralPath $file).Hash -ne $entry.sha256) {throw "Runtime dependency changed: $($entry.relative_path)"}
}
$official='C:\Program Files\Adobe\Common\Plug-ins\7.0\MediaCore\Sapphire Plug-ins\Sapphire Lighting'
$before=@{}
Get-ChildItem -LiteralPath $official -Filter '*.aex' -File | ForEach-Object {$before[$_.Name]=(Get-FileHash -LiteralPath $_.FullName).Hash}
$running=Get-Process | Where-Object {$_.ProcessName -match '^(AfterFX|Adobe Premiere Pro|AdobePremierePro|mocha.*)$'}
if ($running) {throw 'Host started during verification; stopping before deployment'}
New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
$bytes=[IO.File]::ReadAllBytes($Candidate)
$stream=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {$stream.Write($bytes,0,$bytes.Length)} finally {$stream.Dispose()}
if ((Get-FileHash -LiteralPath $dest).Hash -ne $expectedAex) {throw 'Installed readback mismatch'}
foreach ($name in $before.Keys) {
 if ((Get-FileHash -LiteralPath (Join-Path $official $name)).Hash -ne $before[$name]) {throw "Formal entry changed: $name"}
}
$result=[ordered]@{installed=$true;destination=$dest;display_name='S_眩光副本';match_name='T_Glare';aex_sha256=$expectedAex;runtime=$runtime;core_sha256=$expectedCore;formal_entries_unchanged=$before.Count;formal_entry_hashes=$before;mocha_dependency=$mocha;runtime_acceptance='pending';rollback='Close hosts and move only this T_Glare.aex outside the AE plugin scan directory; do not delete shared runtimes.'}
New-Item -ItemType Directory -Path (Split-Path -Parent $Report) -Force | Out-Null
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Report -Encoding UTF8
$result | ConvertTo-Json -Depth 5 -Compress
