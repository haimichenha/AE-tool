[CmdletBinding()]
param(
    [ValidateSet('ascii_quote','gbk_bare','gbk_quote')]
    [string]$Mode = 'ascii_quote',
    [string]$Source = 'D:\tmp\sapphire-patch-lab\sapphire_ae.dll',
    [string]$Destination
)

$ErrorActionPreference = 'Stop'
$needle = 'title freq_rel_x'
$labRoot = [IO.Path]::GetFullPath('D:\tmp\sapphire-patch-lab')
$trialRoot = [IO.Path]::GetFullPath((Join-Path $labRoot 'trials'))

if (-not $Destination) {
    $Destination = Join-Path $trialRoot (Join-Path $Mode 'sapphire_ae.dll')
}
$sourceFull = [IO.Path]::GetFullPath($Source)
$destinationFull = [IO.Path]::GetFullPath($Destination)
if ($sourceFull -eq $destinationFull) { throw 'Source and destination must differ.' }
if (-not $destinationFull.StartsWith($trialRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Destination must remain under $trialRoot"
}
if (Test-Path -LiteralPath $destinationFull) { throw "Refusing to overwrite existing trial: $destinationFull" }

$sourceBytes = [IO.File]::ReadAllBytes($sourceFull)
$sourceText = [Text.Encoding]::Latin1.GetString($sourceBytes)
$offsets = [Collections.Generic.List[int]]::new()
$start = 0
while ($true) {
    $hit = $sourceText.IndexOf($needle, $start, [StringComparison]::Ordinal)
    if ($hit -lt 0) { break }
    $offsets.Add($hit)
    $start = $hit + 1
}
if ($offsets.Count -ne 1) { throw "Expected exactly one '$needle' occurrence; found $($offsets.Count)." }

$replacementText = switch ($Mode) {
    'ascii_quote' { 'title "Probe"   ' }
    'gbk_bare'    { $null }
    'gbk_quote'   { $null }
}
if ($Mode -eq 'ascii_quote') {
    $replacementBytes = [Text.Encoding]::ASCII.GetBytes($replacementText)
} else {
    $gbk = [Text.Encoding]::GetEncoding(936)
    $cn = $gbk.GetBytes('环境亮度')
    $prefix = [Text.Encoding]::ASCII.GetBytes('title ')
    if ($Mode -eq 'gbk_bare') {
        $suffix = [Text.Encoding]::ASCII.GetBytes('  ')
        $replacementBytes = $prefix + $cn + $suffix
    } else {
        $quote = [Text.Encoding]::ASCII.GetBytes('"')
        $replacementBytes = $prefix + $quote + $cn + $quote
    }
}
$needleBytes = [Text.Encoding]::ASCII.GetBytes($needle)
if ($replacementBytes.Length -ne $needleBytes.Length) {
    throw "Patch length mismatch: replacement=$($replacementBytes.Length), target=$($needleBytes.Length)."
}
$offset = $offsets[0]
for ($i = 0; $i -lt $needleBytes.Length; $i++) {
    if ($sourceBytes[$offset + $i] -ne $needleBytes[$i]) { throw "Preimage mismatch at 0x$('{0:X}' -f ($offset + $i))." }
}
$outBytes = [byte[]]$sourceBytes.Clone()
[Array]::Copy($replacementBytes, 0, $outBytes, $offset, $replacementBytes.Length)
for ($i = 0; $i -lt $replacementBytes.Length; $i++) {
    if ($outBytes[$offset + $i] -ne $replacementBytes[$i]) { throw "Postimage verification failed at 0x$('{0:X}' -f ($offset + $i))." }
}

$destDir = Split-Path -Parent $destinationFull
[IO.Directory]::CreateDirectory($destDir) | Out-Null
[IO.File]::WriteAllBytes($destinationFull, $outBytes)
$manifest = [ordered]@{
    mode = $Mode
    source = $sourceFull
    source_sha256 = (Get-FileHash -LiteralPath $sourceFull -Algorithm SHA256).Hash
    destination = $destinationFull
    destination_sha256 = (Get-FileHash -LiteralPath $destinationFull -Algorithm SHA256).Hash
    offset = ('0x{0:X}' -f $offset)
    preimage_ascii = $needle
    replacement_hex = ([Convert]::ToHexString($replacementBytes))
    byte_length = $replacementBytes.Length
    created_at_utc = [DateTime]::UtcNow.ToString('o')
}
$manifestPath = Join-Path $destDir 'manifest.json'
$manifest | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding utf8
$manifest | ConvertTo-Json -Compress
