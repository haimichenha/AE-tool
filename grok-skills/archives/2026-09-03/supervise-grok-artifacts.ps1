[CmdletBinding()]
param(
    [Parameter(Mandatory)][string[]]$ArtifactPath,
    [Parameter(Mandatory)][string]$Objective,
    [ValidateRange(1,2)][int]$MaxAttemptsPerArtifact = 2,
    [ValidateRange(0.05,2.00)][decimal]$MaxBudgetUsd = 0.30,
    [string]$Model = 'grok-4.6'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$cfg = Get-Content -LiteralPath (Join-Path $HOME '.claude\settings.json') -Raw | ConvertFrom-Json
$env:ANTHROPIC_API_KEY = [string]$cfg.env.ANTHROPIC_AUTH_TOKEN
$env:ANTHROPIC_BASE_URL = [string]$cfg.env.ANTHROPIC_BASE_URL
$exe = Join-Path $env:APPDATA 'npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Missing Claude executable: $exe" }

$reports = [System.Collections.Generic.List[object]]::new()
foreach ($artifact in $ArtifactPath) {
    if (-not (Test-Path -LiteralPath $artifact)) {
        $reports.Add([pscustomobject]@{ path=$artifact; status='missing'; report='' })
        continue
    }
    $full = (Get-Item -LiteralPath $artifact).FullName
    $name = Split-Path -Leaf $full
    $parent = Split-Path -Parent $full
    $accepted = $false
    $last = ''
    for ($attempt = 1; $attempt -le $MaxAttemptsPerArtifact; $attempt++) {
        Write-Output "GROK_SUPERVISOR_ARTIFACT=$name attempt=$attempt/$MaxAttemptsPerArtifact"
        $system = 'You are a Chinese evidence reader. Use Read on the exact requested file before answering. Do not give a plan, menu, or generic summary. State only facts present in the file and their implication for the stated objective.'
        $prompt = @"
Objective: $Objective
Exact artifact to read now: $full
Use a read-only tool to read this file. Then return Chinese text with exactly these labels:
PATH: the exact path
FACTS: at least two concrete facts from file content
IMPLICATION: what those facts mean for the objective
Do not inspect binaries, do not modify files, and do not ask for confirmation.
Previous insufficient report: $last
"@
        Push-Location -LiteralPath $parent
        try {
            $raw = & $exe --bare -p --model $Model --effort high --no-session-persistence --disable-slash-commands --permission-mode auto '--allowed-tools=Read,Glob,Grep,LS' --max-budget-usd ([string]$MaxBudgetUsd) --output-format json --system-prompt $system $prompt
            $exitCode = $LASTEXITCODE
        } finally { Pop-Location }
        try { $last = [string](($raw | Out-String | ConvertFrom-Json -ErrorAction Stop).result) } catch { $last = '' }
        if ($exitCode -eq 0 -and $last.Length -ge 120 -and $last.Contains($name) -and $last -match 'FACTS:') { $accepted = $true; break }
    }
    $reports.Add([pscustomobject]@{ path=$full; status=if($accepted){'accepted'}else{'insufficient'}; report=$last })
}

$acceptedReports = @($reports | Where-Object status -eq 'accepted')
$synthesis = ''
if ($acceptedReports.Count -gt 0) {
    Write-Output "GROK_SUPERVISOR_PHASE=synthesis accepted=$($acceptedReports.Count)/$($reports.Count)"
    $evidence = $acceptedReports | ConvertTo-Json -Depth 5 -Compress
    $root = Split-Path -Parent $acceptedReports[0].path
    $system = 'You are a Chinese technical synthesizer. Use only supplied evidence reports. Do not invent facts, do not provide menus, and distinguish verified conclusions from missing evidence.'
    $prompt = "Objective: $Objective`nEvidence reports: $evidence`nProduce: verified cross-file conclusions; failed or unsupported paths; one safe next action."
    Push-Location -LiteralPath $root
    try {
        $raw = & $exe --bare -p --model $Model --effort high --no-session-persistence --disable-slash-commands --permission-mode auto '--allowed-tools=Read,Glob,Grep,LS' --max-budget-usd ([string]$MaxBudgetUsd) --output-format json --system-prompt $system $prompt
    } finally { Pop-Location }
    try { $synthesis = [string](($raw | Out-String | ConvertFrom-Json -ErrorAction Stop).result) } catch { $synthesis = '' }
}

[pscustomobject]@{ model=$Model; reports=@($reports); synthesis=$synthesis } | ConvertTo-Json -Depth 10
