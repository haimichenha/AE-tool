$ErrorActionPreference='Stop'
$expected=@{
'Q_BokehLights.aex'='F209F292AC4FDEE9CEB97E290466413FEC1D444B7F94DD7EE6CFB5CCF9C9FB94'
'Q_EdgeRays.aex'='480263DB8ED2CB344F402A7BD1A619A3593C0D9D80CC537AF55C4EE0D38F510A'
'Q_Flashbulbs.aex'='68A32203EB2A0B06A6DA676193B4D321DC0DDD285B7D68354977AD6D15B3BAAC'
'Q_Glint.aex'='709F86036A7D9D86F07889699780ADF67967361A8B94BDF1F87D69D957DE0101'
'Q_Glow.aex'='A9427B8007284E371C81B302D2FFC74E40F209EB806DB2F5D80EE5A4CEFA376D'
'Q_Streaks.aex'='3A1E921326B477CB05689C02055757E2F0F5CC225A03A74672276FBC057A5836'
}

$source='D:\tmp\lighting-batch01-20260910\aex'
$dest='D:\AZBao\PR 22\Ae2022\Adobe After Effects 2025\Support Files\Plug-ins\Effects\Sapphire Patch Lab'
$report='D:\tmp\lighting-batch01-20260910\deployment.json'
if(Test-Path -LiteralPath $report){throw 'Deployment report already exists'}
if(Get-Process | Where-Object {$_.ProcessName -match '^(AfterFX|AdobePremierePro|Adobe Premiere Pro|mocha.*)$'}){throw 'Close hosts; nothing will be killed'}
if((Get-FileHash -LiteralPath 'D:\tmp\saprt\lights01\lib64\sapphire_ae.dll').Hash -ne '3DA5AF307B0B0B15B9B950AD9BB84A0CD33284F8174D52397EF1D97B4EBFCCE3'){throw 'Core mismatch'}
foreach($name in $expected.Keys){
 if(Test-Path -LiteralPath (Join-Path $dest $name)){throw "Existing entry: $name"}
 if((Get-FileHash -LiteralPath (Join-Path $source $name)).Hash -ne $expected[$name]){throw "Candidate mismatch: $name"}
}
$official='C:\Program Files\Adobe\Common\Plug-ins\7.0\MediaCore\Sapphire Plug-ins\Sapphire Lighting'
$before=@{};Get-ChildItem -LiteralPath $official -Filter '*.aex' -File | ForEach-Object {$before[$_.Name]=(Get-FileHash -LiteralPath $_.FullName).Hash}
$installed=@()
foreach($name in $expected.Keys){
 $path=Join-Path $dest $name;$bytes=[IO.File]::ReadAllBytes((Join-Path $source $name))
 $s=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$s.Write($bytes,0,$bytes.Length)}finally{$s.Dispose()}
 if((Get-FileHash -LiteralPath $path).Hash -ne $expected[$name]){throw 'Readback mismatch'}
 $installed+=$path
}
foreach($name in $before.Keys){if((Get-FileHash -LiteralPath (Join-Path $official $name)).Hash -ne $before[$name]){throw 'Formal entry changed'}}
@{installed=$installed;hashes=$expected;formal_entries_unchanged=$before.Count;runtime='D:\tmp\saprt\lights01';runtime_validation='pending';rollback='Close hosts, move only these six Q_*.aex files out of the plugin scan folder; preserve runtimes.'} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $report -Encoding UTF8
Get-Content -LiteralPath $report -Raw