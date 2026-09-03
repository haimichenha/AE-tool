[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$TrialCore,
    [string]$RuntimeRoot = 'D:\tmp\saprt\title',
    [string]$SourceRoot = 'C:\Program Files\BorisFX\Sapphire 2024 Adobe'
)

$ErrorActionPreference = 'Stop'
$runtimeFull = [IO.Path]::GetFullPath($RuntimeRoot)
$allowed = [IO.Path]::GetFullPath('D:\tmp\saprt')
if (-not $runtimeFull.StartsWith($allowed + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "RuntimeRoot must remain under $allowed"
}
if (Test-Path -LiteralPath $runtimeFull) { throw "Refusing to overwrite existing runtime: $runtimeFull" }
if (-not (Test-Path -LiteralPath $TrialCore)) { throw "Missing trial core: $TrialCore" }

$originalCore = Join-Path $SourceRoot 'lib64\sapphire_ae.dll'
$originalAex = Join-Path $SourceRoot 'plugins64\Sapphire Plug-ins\Sapphire Transitions\S_WipeFlux.aex'
if ((Get-FileHash -LiteralPath $originalCore -Algorithm SHA256).Hash -ne '3A01082AD1D1F3189B9929B717BFD384FB5676BB0BC927F9E2141FAF54C07482') {
    throw 'Installed core hash is not the recorded baseline; refusing to stage runtime.'
}

New-Item -ItemType Directory -Path $runtimeFull | Out-Null
Copy-Item -LiteralPath (Join-Path $SourceRoot 'lib64') -Destination (Join-Path $runtimeFull 'lib64') -Recurse
foreach ($name in 's_config.text','s_filmtypes.text','s_function_list.text','sapphire-app-settings.ini') {
    Copy-Item -LiteralPath (Join-Path $SourceRoot $name) -Destination (Join-Path $runtimeFull $name)
}
$aexDest = Join-Path $runtimeFull 'plugins64\Sapphire Plug-ins\Sapphire Transitions\S_WipeFlux.aex'
New-Item -ItemType Directory -Path (Split-Path -Parent $aexDest) -Force | Out-Null
Copy-Item -LiteralPath $originalAex -Destination $aexDest
Copy-Item -LiteralPath $TrialCore -Destination (Join-Path $runtimeFull 'lib64\sapphire_ae.dll') -Force

$oldRoot = 'c:/Program Files/BorisFX/Sapphire 2024 Adobe'
$newRoot = $runtimeFull.Replace('\','/')
$oldBytes = [Text.Encoding]::ASCII.GetBytes($oldRoot)
$newBytes = [Text.Encoding]::ASCII.GetBytes($newRoot)
if ($newBytes.Length -gt $oldBytes.Length) { throw 'Runtime root is too long for the in-place test AEX path field.' }
$aex = [IO.File]::ReadAllBytes($aexDest)
$aexText = [Text.Encoding]::Latin1.GetString($aex)
$first = $aexText.IndexOf($oldRoot, [StringComparison]::Ordinal)
if ($first -lt 0 -or $aexText.IndexOf($oldRoot, $first + 1, [StringComparison]::Ordinal) -ge 0) {
    throw 'Expected exactly one hardcoded Sapphire root field in the test AEX.'
}
for ($i = 0; $i -lt $oldBytes.Length; $i++) {
    if ($aex[$first + $i] -ne $oldBytes[$i]) { throw 'AEX root preimage mismatch.' }
}
[Array]::Clear($aex, $first, $oldBytes.Length)
[Array]::Copy($newBytes, 0, $aex, $first, $newBytes.Length)
[IO.File]::WriteAllBytes($aexDest, $aex)

$manifest = [ordered]@{
    runtime_root = $runtimeFull
    trial_core = [IO.Path]::GetFullPath($TrialCore)
    trial_core_sha256 = (Get-FileHash -LiteralPath $TrialCore -Algorithm SHA256).Hash
    runtime_core_sha256 = (Get-FileHash -LiteralPath (Join-Path $runtimeFull 'lib64\sapphire_ae.dll') -Algorithm SHA256).Hash
    test_aex = $aexDest
    test_aex_sha256 = (Get-FileHash -LiteralPath $aexDest -Algorithm SHA256).Hash
    aex_root_offset = ('0x{0:X}' -f $first)
    original_root = $oldRoot
    test_root = $newRoot
    created_at_utc = [DateTime]::UtcNow.ToString('o')
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeFull 'runtime-manifest.json') -Encoding utf8
$manifest | ConvertTo-Json -Compress
