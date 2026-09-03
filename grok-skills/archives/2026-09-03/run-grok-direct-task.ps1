[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Task,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string[]]$TargetPath,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string[]]$AcceptanceCriteria,
    [ValidateSet('ReadOnly','Implement')][string]$Mode = 'Implement',
    [ValidateRange(1,3)][int]$MaxAttempts = 2,
    [ValidateRange(0.05,5.00)][decimal]$MaxBudgetUsd = 0.75,
    [string]$Model = 'grok-4.6'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Stop-Direct([string]$Message) { throw "grok-direct-task: $Message" }

$roots = [System.Collections.Generic.List[object]]::new()
foreach ($path in $TargetPath) {
    if (-not (Test-Path -LiteralPath $path)) { Stop-Direct "Target path does not exist: $path" }
    $item = Get-Item -LiteralPath $path -Force
    $roots.Add([pscustomobject]@{
        path = $item.FullName
        kind = if ($item.PSIsContainer) { 'directory' } else { 'file' }
    })
}

$settingsPath = Join-Path $HOME '.claude\settings.json'
$settings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
$baseUrl = [string]$settings.env.ANTHROPIC_BASE_URL
$authToken = [string]$settings.env.ANTHROPIC_AUTH_TOKEN
if ([string]::IsNullOrWhiteSpace($baseUrl) -or [string]::IsNullOrWhiteSpace($authToken)) {
    Stop-Direct 'Claude settings are missing provider credentials.'
}
$exe = Join-Path $env:APPDATA 'npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe'
if (-not (Test-Path -LiteralPath $exe)) { Stop-Direct "Missing Claude executable: $exe" }

$criteria = for ($index = 0; $index -lt $AcceptanceCriteria.Count; $index++) {
    [pscustomobject]@{ id = "A$($index + 1)"; text = $AcceptanceCriteria[$index] }
}
$toolList = if ($Mode -eq 'ReadOnly') { 'Bash,Read,Glob,Grep,LS' } else { 'Bash,Read,Glob,Grep,LS,Write,Edit' }
$systemPrompt = @"
You are a Chinese software execution agent. Use filesystem tools directly; do not merely describe commands.
Work only inside the supplied target roots. First inspect the target with LS, Glob, Read, or Bash. Then perform the task, verify the result with tools, and continue until every criterion is satisfied or a real blocker is proven.
Do not ask A/B/C questions or produce an AS routing summary. A directory listing is only phase 1: for every named script, reference, state, configuration, or text artifact, read its content and cite a concrete fact before concluding. Then compare artifacts and continue through all acceptance criteria. Do not claim a change without reading back evidence.
Your final response must be JSON only with this exact shape:
{"status":"completed|blocked","completed_criteria":["A1"],"verification":["path and observed result"],"remaining_work":[],"next_action":""}
"@

$previousKey = $env:ANTHROPIC_API_KEY
$previousUrl = $env:ANTHROPIC_BASE_URL
$env:ANTHROPIC_API_KEY = $authToken
$env:ANTHROPIC_BASE_URL = $baseUrl
$retry = ''
$final = $null

try {
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $prompt = @"
Execute the following task now.
MODE: $Mode
TARGET ROOTS: $($roots | ConvertTo-Json -Compress)
TASK: $Task
ACCEPTANCE CRITERIA: $($criteria | ConvertTo-Json -Compress)
PREVIOUS RESULT DEFECT: $retry
For ReadOnly mode, never modify, run installers, download, delete, or copy files. For Implement mode, make only necessary reversible changes inside the target roots.
"@
        $workdir = if ($roots[0].kind -eq 'directory') { $roots[0].path } else { Split-Path -Parent $roots[0].path }
        Write-Output "GROK_DIRECT_PHASE=$attempt/$MaxAttempts mode=$Mode action=inspect-act-verify"
        Push-Location -LiteralPath $workdir
        try {
            $raw = & $exe --bare -p --model $Model --effort high --no-session-persistence --disable-slash-commands --permission-mode auto "--allowed-tools=$toolList" --max-budget-usd ([string]$MaxBudgetUsd) --output-format json --system-prompt $systemPrompt $prompt
            $exitCode = $LASTEXITCODE
        }
        finally { Pop-Location }

        try {
            $cli = ($raw | Out-String | ConvertFrom-Json -ErrorAction Stop)
            $result = ([string]$cli.result | ConvertFrom-Json -ErrorAction Stop)
        }
        catch {
            $retry = 'Final response was not the required JSON contract.'
            continue
        }

        $requiredFields = @('status','completed_criteria','verification','remaining_work','next_action')
        $missing = @($requiredFields | Where-Object { $null -eq $result.PSObject.Properties[$_] })
        if ($missing.Count -gt 0) {
            $retry = 'Final JSON omitted required fields: ' + ($missing -join ', ') + '. Read remaining artifacts and return the exact contract.'
            continue
        }

        $expected = @($criteria.id)
        $actual = @($result.completed_criteria)
        $valid = $exitCode -eq 0 -and [string]$result.status -eq 'completed' -and @($result.verification).Count -gt 0 -and @($result.remaining_work).Count -eq 0 -and @($expected | Where-Object { $_ -notin $actual }).Count -eq 0
        if ($valid) {
            $final = [pscustomobject]@{ success=$true; attempts=$attempt; model=$Model; mode=$Mode; result=$result }
            break
        }
        $retry = 'The acceptance contract was incomplete. Re-inspect files, finish the remaining criteria, and return valid JSON.'
    }
}
finally {
    $env:ANTHROPIC_API_KEY = $previousKey
    $env:ANTHROPIC_BASE_URL = $previousUrl
}

if ($null -eq $final) {
    $final = [pscustomobject]@{ success=$false; model=$Model; mode=$Mode; error='Same-model direct execution did not satisfy the acceptance contract.' }
}
$final | ConvertTo-Json -Depth 12
