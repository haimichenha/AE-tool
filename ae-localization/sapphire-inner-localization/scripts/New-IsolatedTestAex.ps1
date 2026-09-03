[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$SourceAex,
    [Parameter(Mandatory)] [string]$DestinationAex,
    [Parameter(Mandatory)] [string]$OriginalEffectName,
    [Parameter(Mandatory)] [string]$TestEffectName,
    [Parameter(Mandatory)] [string]$RuntimeRoot
)

$ErrorActionPreference = 'Stop'
$runtimeFull = [IO.Path]::GetFullPath($RuntimeRoot)
$destinationFull = [IO.Path]::GetFullPath($DestinationAex)
if (-not $destinationFull.StartsWith($runtimeFull + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Destination must remain inside the isolated runtime.' }
if (Test-Path -LiteralPath $destinationFull) { throw "Refusing to overwrite $destinationFull" }
$oldName = [Text.Encoding]::ASCII.GetBytes($OriginalEffectName)
$newName = [Text.Encoding]::ASCII.GetBytes($TestEffectName)
if ($oldName.Length -ne $newName.Length) { throw 'Test effect identity must have identical byte length.' }
$oldRoot = 'c:/Program Files/BorisFX/Sapphire 2024 Adobe'
$newRoot = $runtimeFull.Replace('\','/')
$oldRootBytes = [Text.Encoding]::ASCII.GetBytes($oldRoot)
$newRootBytes = [Text.Encoding]::ASCII.GetBytes($newRoot)
if ($newRootBytes.Length -gt $oldRootBytes.Length) { throw 'Runtime root is too long for the test AEX path field.' }

$bytes = [IO.File]::ReadAllBytes([IO.Path]::GetFullPath($SourceAex))
$sourceHash = (Get-FileHash -LiteralPath $SourceAex -Algorithm SHA256).Hash
$text = [Text.Encoding]::Latin1.GetString($bytes)
$rootOffset = $text.IndexOf($oldRoot, [StringComparison]::Ordinal)
if ($rootOffset -lt 0 -or $text.IndexOf($oldRoot, $rootOffset + 1, [StringComparison]::Ordinal) -ge 0) { throw 'Expected exactly one AEX core-root field.' }
[Array]::Clear($bytes, $rootOffset, $oldRootBytes.Length)
[Array]::Copy($newRootBytes, 0, $bytes, $rootOffset, $newRootBytes.Length)

$patterns = @(
    [byte[]]([Text.Encoding]::ASCII.GetBytes('eman') + [byte[]](0,0,0,0,0x0C,0,0,0,$oldName.Length) + $oldName),
    [byte[]]([Text.Encoding]::ASCII.GetBytes('ANMe') + [byte[]](0,0,0,0,0x0C,0,0,0,$oldName.Length) + $oldName)
)
$identityOffsets = @()
foreach ($pattern in $patterns) {
    $found = [Collections.Generic.List[int]]::new()
    for ($i = 0; $i -le $bytes.Length - $pattern.Length; $i++) {
        $same = $true
        for ($j = 0; $j -lt $pattern.Length; $j++) { if ($bytes[$i + $j] -ne $pattern[$j]) { $same = $false; break } }
        if ($same) { $found.Add($i) }
    }
    if ($found.Count -ne 1) { throw "Expected exactly one PiPL identity field; found $($found.Count)." }
    $offset = $found[0] + $pattern.Length - $oldName.Length
    [Array]::Copy($newName, 0, $bytes, $offset, $newName.Length)
    $identityOffsets += ('0x{0:X}' -f $offset)
}

New-Item -ItemType Directory -Path (Split-Path -Parent $destinationFull) -Force | Out-Null
[IO.File]::WriteAllBytes($destinationFull, $bytes)
$manifest = [ordered]@{
    source = [IO.Path]::GetFullPath($SourceAex)
    source_sha256 = $sourceHash
    destination = $destinationFull
    destination_sha256 = (Get-FileHash -LiteralPath $destinationFull -Algorithm SHA256).Hash
    original_effect_identity = $OriginalEffectName
    test_effect_identity = $TestEffectName
    pipl_identity_offsets = $identityOffsets
    aex_root_offset = ('0x{0:X}' -f $rootOffset)
    runtime_root = $runtimeFull
    created_at_utc = [DateTime]::UtcNow.ToString('o')
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath ((Split-Path -Parent $destinationFull) + '\' + $TestEffectName + '.manifest.json') -Encoding utf8
$manifest | ConvertTo-Json -Compress
