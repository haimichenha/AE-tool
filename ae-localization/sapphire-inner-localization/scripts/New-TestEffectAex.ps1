[CmdletBinding()]
param(
    [string]$Source = 'D:\tmp\saprt\title\plugins64\Sapphire Plug-ins\Sapphire Transitions\S_WipeFlux.aex',
    [string]$Destination = 'D:\tmp\saprt\title\plugins64\Sapphire Plug-ins\Sapphire Transitions\T_WipeFlux.aex'
)

$ErrorActionPreference = 'Stop'
$sourceFull = [IO.Path]::GetFullPath($Source)
$destinationFull = [IO.Path]::GetFullPath($Destination)
$runtimeRoot = [IO.Path]::GetFullPath('D:\tmp\saprt\title')
if (-not $destinationFull.StartsWith($runtimeRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Destination must remain inside the isolated runtime.' }
if (Test-Path -LiteralPath $destinationFull) { throw "Refusing to overwrite $destinationFull" }

$oldName = [Text.Encoding]::ASCII.GetBytes('S_WipeFlux')
$newName = [Text.Encoding]::ASCII.GetBytes('T_WipeFlux')
$bytes = [IO.File]::ReadAllBytes($sourceFull)
$patterns = @(
    [byte[]]([Text.Encoding]::ASCII.GetBytes('eman') + [byte[]](0,0,0,0,0x0C,0,0,0,0x0A) + $oldName),
    [byte[]]([Text.Encoding]::ASCII.GetBytes('ANMe') + [byte[]](0,0,0,0,0x0C,0,0,0,0x0A) + $oldName)
)
$changes = @()
foreach ($pattern in $patterns) {
    $found = [Collections.Generic.List[int]]::new()
    for ($i = 0; $i -le $bytes.Length - $pattern.Length; $i++) {
        $same = $true
        for ($j = 0; $j -lt $pattern.Length; $j++) { if ($bytes[$i + $j] -ne $pattern[$j]) { $same = $false; break } }
        if ($same) { $found.Add($i) }
    }
    if ($found.Count -ne 1) { throw "Expected exactly one PiPL identity field; found $($found.Count)." }
    $offset = $found[0] + $pattern.Length - $oldName.Length
    for ($j = 0; $j -lt $oldName.Length; $j++) { if ($bytes[$offset + $j] -ne $oldName[$j]) { throw 'PiPL name preimage mismatch.' } }
    [Array]::Copy($newName, 0, $bytes, $offset, $newName.Length)
    $changes += ('0x{0:X}' -f $offset)
}

[IO.File]::WriteAllBytes($destinationFull, $bytes)
$manifest = [ordered]@{
    source = $sourceFull
    source_sha256 = (Get-FileHash -LiteralPath $sourceFull -Algorithm SHA256).Hash
    destination = $destinationFull
    destination_sha256 = (Get-FileHash -LiteralPath $destinationFull -Algorithm SHA256).Hash
    pipl_identity_offsets = $changes
    old_identity = 'S_WipeFlux'
    test_identity = 'T_WipeFlux'
    created_at_utc = [DateTime]::UtcNow.ToString('o')
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path (Split-Path -Parent $destinationFull) 'T_WipeFlux.manifest.json') -Encoding utf8
$manifest | ConvertTo-Json -Compress
