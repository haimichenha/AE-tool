[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Task,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string[]]$TargetPath,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string[]]$AcceptanceCriteria,
    [ValidateSet('ReadOnly','Implement')][string]$Mode = 'Implement',
    [ValidateRange(1,8)][int]$MaxAttempts = 3,
    [ValidateRange(0.05,20.00)][decimal]$MaxBudgetUsd = 0.75,
    [string]$Model = 'claude-sonnet-4-6',
    [ValidateRange(30,3600)][int]$TimeoutSeconds = 300,
    [string]$RunId,
    [switch]$SkipModelPreflight
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# stdout carries the final JSON document and nothing else. Every progress line
# goes to stderr so the caller can pipe stdout straight into ConvertFrom-Json.
# ---------------------------------------------------------------------------
function Write-Progress-Line([string]$Message) {
    [Console]::Error.WriteLine("GROK_DIRECT $Message")
}

function New-Slug([string]$Text) {
    $clean = ($Text -replace '[^A-Za-z0-9]+', '-').Trim('-').ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($clean)) { $clean = 'task' }
    if ($clean.Length -gt 32) { $clean = $clean.Substring(0, 32).Trim('-') }
    return $clean
}

# Emits the final document and exits. Used by every terminal path so the caller
# always receives parseable JSON, including on hard failure.
function Complete-Run($Document) {
    $Document | ConvertTo-Json -Depth 14
    exit 0
}

$startedUtc = [DateTime]::UtcNow

# Assigned for real further down, but Save-State can fire on an early-exit path
# before that point, and StrictMode makes an unassigned read fatal.
$script:criteria = @()

# --- resolve target roots ---------------------------------------------------
$roots = [System.Collections.Generic.List[object]]::new()
foreach ($path in $TargetPath) {
    if (-not (Test-Path -LiteralPath $path)) {
        Complete-Run ([pscustomobject]@{
            success = $false; status = 'failed'; failure_class = 'hard'
            model = $Model; mode = $Mode
            error = "Target path does not exist: $path"
        })
    }
    $item = Get-Item -LiteralPath $path -Force
    $roots.Add([pscustomobject]@{
        path = $item.FullName
        kind = if ($item.PSIsContainer) { 'directory' } else { 'file' }
    })
}

# --- run directory (diagnostics survive every failure) ----------------------
$runsRoot = Join-Path $HOME '.claude\grok-runs'
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = '{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), (New-Slug $Task)
}
$runDir = Join-Path $runsRoot $RunId
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$statePath = Join-Path $runDir 'state.json'

$attemptLog = [System.Collections.Generic.List[object]]::new()
$resumedFrom = 0
if (Test-Path -LiteralPath $statePath) {
    try {
        $prior = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        if ($null -ne $prior.PSObject.Properties['attempts']) {
            foreach ($a in @($prior.attempts)) { $attemptLog.Add($a) }
            $resumedFrom = $attemptLog.Count
        }
    }
    catch { $resumedFrom = 0 }
}

function Save-State([string]$Status, $Extra) {
    $state = [pscustomobject]@{
        run_id      = $RunId
        status      = $Status
        started_utc = $startedUtc.ToString('o')
        updated_utc = ([DateTime]::UtcNow).ToString('o')
        task        = $Task
        mode        = $Mode
        model       = $Model
        targets     = @($roots)
        criteria    = @($script:criteria)
        max_attempts    = $MaxAttempts
        base_budget_usd = $MaxBudgetUsd
        timeout_seconds = $TimeoutSeconds
        resumed_from_attempt = $resumedFrom
        attempts    = @($attemptLog)
        extra       = $Extra
    }
    $state | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $statePath -Encoding UTF8
}

function Get-Handoff([string]$Class) {
    return [pscustomobject]@{
        run_dir      = $runDir
        state_file   = $statePath
        raw_attempts = @(Get-ChildItem -LiteralPath $runDir -Filter 'attempt-*.raw.txt' -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
        failure_class = $Class
        resume_command = "& '$PSCommandPath' -RunId '$RunId' -Task <same> -TargetPath <same> -AcceptanceCriteria <same> -Mode $Mode -Model $Model"
    }
}

# --- credentials ------------------------------------------------------------
$settingsPath = Join-Path $HOME '.claude\settings.json'
if (-not (Test-Path -LiteralPath $settingsPath)) {
    Save-State 'failed' 'settings.json missing'
    Complete-Run ([pscustomobject]@{
        success = $false; status = 'failed'; failure_class = 'hard'; model = $Model; mode = $Mode
        error = "Claude settings not found: $settingsPath"; run_dir = $runDir; handoff = (Get-Handoff 'hard')
    })
}
$settings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
$baseUrl = [string]$settings.env.ANTHROPIC_BASE_URL
$authToken = [string]$settings.env.ANTHROPIC_AUTH_TOKEN
if ([string]::IsNullOrWhiteSpace($baseUrl) -or [string]::IsNullOrWhiteSpace($authToken)) {
    Save-State 'failed' 'missing credentials'
    Complete-Run ([pscustomobject]@{
        success = $false; status = 'failed'; failure_class = 'hard'; model = $Model; mode = $Mode
        error = 'Claude settings are missing provider credentials.'; run_dir = $runDir; handoff = (Get-Handoff 'hard')
    })
}

$exe = Join-Path $env:APPDATA 'npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe'
if (-not (Test-Path -LiteralPath $exe)) {
    Save-State 'failed' 'claude.exe missing'
    Complete-Run ([pscustomobject]@{
        success = $false; status = 'failed'; failure_class = 'hard'; model = $Model; mode = $Mode
        error = "Missing Claude executable: $exe"; run_dir = $runDir; handoff = (Get-Handoff 'hard')
    })
}

# --- model preflight --------------------------------------------------------
# A model the gateway does not route is a permanent condition. Catching it here
# costs one HTTP call; missing it costs MaxAttempts full-length timeouts, and
# the model gets blamed for what is really a routing failure.
if (-not $SkipModelPreflight) {
    try {
        $catalog = Invoke-RestMethod -Uri "$($baseUrl.TrimEnd('/'))/v1/models" -TimeoutSec 30 `
            -Headers @{ 'Authorization' = "Bearer $authToken"; 'x-api-key' = $authToken; 'anthropic-version' = '2023-06-01' }
        $available = @($catalog.data.id)
        $configuredModels = @(
            [string]$settings.env.ANTHROPIC_DEFAULT_OPUS_MODEL,
            [string]$settings.env.ANTHROPIC_DEFAULT_SONNET_MODEL,
            [string]$settings.env.ANTHROPIC_DEFAULT_HAIKU_MODEL
        ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique
        $configuredAlias = $Model -in @($configuredModels)
        if ($available.Count -gt 0 -and $Model -notin $available -and -not $configuredAlias) {
            Save-State 'failed' "model '$Model' not served by gateway"
            Complete-Run ([pscustomobject]@{
                success = $false; status = 'failed'; failure_class = 'hard'; model = $Model; mode = $Mode
                error = "Gateway $baseUrl does not serve model '$Model'. Pass -Model with a served id, or -SkipModelPreflight to bypass."
                available_models = ($available | Sort-Object)
                run_dir = $runDir; handoff = (Get-Handoff 'hard')
            })
        }
        if ($available.Count -gt 0 -and $Model -notin $available -and $configuredAlias) {
            Write-Progress-Line "preflight catalog omits configured alias model=$Model; proceeding to bounded actual call"
        }
        else {
            Write-Progress-Line "preflight ok model=$Model served_models=$($available.Count)"
        }
    }
    catch {
        # Catalog unreachable is not proof the model is bad; continue and let the
        # per-attempt classifier judge the real call.
        Write-Progress-Line "preflight skipped (catalog unreachable): $($_.Exception.Message)"
    }
}

# --- prompt scaffolding -----------------------------------------------------
$script:criteria = @(for ($index = 0; $index -lt $AcceptanceCriteria.Count; $index++) {
    [pscustomobject]@{ id = "A$($index + 1)"; text = $AcceptanceCriteria[$index] }
})
$toolList = if ($Mode -eq 'ReadOnly') { 'Bash,Read,Glob,Grep,LS' } else { 'Bash,Read,Glob,Grep,LS,Write,Edit' }
$systemPrompt = @"
You are a Chinese software execution agent. Use filesystem tools directly; do not merely describe commands.
Work only inside the supplied target roots. First inspect the target with LS, Glob, Read, or Bash. Then perform the task, verify the result with tools, and continue until every criterion is satisfied or a real blocker is proven.
Do not ask A/B/C questions or produce an AS routing summary. A directory listing is only phase 1: for every named script, reference, state, configuration, or text artifact, read its content and cite a concrete fact before concluding. Then compare artifacts and continue through all acceptance criteria. Do not claim a change without reading back evidence.
Report status "blocked" only when you have concrete evidence that the task cannot be completed; include that evidence in verification. Never report "blocked" merely because the work is large.
Your final response must be JSON only with this exact shape:
{"status":"completed|blocked","completed_criteria":["A1"],"verification":["path and observed result"],"remaining_work":[],"next_action":""}
"@

$workdir = if ($roots[0].kind -eq 'directory') { $roots[0].path } else { Split-Path -Parent $roots[0].path }

# --- transport: bounded, deadlock-free child process -------------------------
# ArgumentList avoids quoting hell; async readers avoid pipe-buffer deadlock;
# WaitForExit(ms) means a wedged child can never hang the runner forever.
function Invoke-ClaudeCli([string[]]$Arguments, [int]$TimeoutMs) {
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $exe
    foreach ($a in $Arguments) { [void]$psi.ArgumentList.Add($a) }
    $psi.WorkingDirectory = $workdir
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardInput = $true
    $psi.Environment['ANTHROPIC_API_KEY'] = $authToken
    $psi.Environment['ANTHROPIC_BASE_URL'] = $baseUrl

    $proc = [System.Diagnostics.Process]::new()
    $proc.StartInfo = $psi
    [void]$proc.Start()
    $proc.StandardInput.Close()
    $outTask = $proc.StandardOutput.ReadToEndAsync()
    $errTask = $proc.StandardError.ReadToEndAsync()

    if (-not $proc.WaitForExit($TimeoutMs)) {
        try { $proc.Kill($true) } catch { }
        try { [void]$proc.WaitForExit(10000) } catch { }
        return [pscustomobject]@{ timedOut = $true; exitCode = -1; stdout = ''; stderr = "Killed after ${TimeoutMs}ms." }
    }
    $proc.WaitForExit()   # flush the async readers
    return [pscustomobject]@{
        timedOut = $false
        exitCode = $proc.ExitCode
        stdout   = $outTask.GetAwaiter().GetResult()
        stderr   = $errTask.GetAwaiter().GetResult()
    }
}

# --- contract extraction -----------------------------------------------------
# StrictMode makes a missing-property read fatal, and the CLI envelope is not
# uniform: the budget-exhausted envelope carries no 'result' property at all.
# Every envelope field must therefore be read through this helper.
function Get-Prop($Object, [string]$Name, $Default = $null) {
    if ($null -eq $Object) { return $Default }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) { return $Default }
    if ($null -eq $prop.Value) { return $Default }
    return $prop.Value
}

# Models routinely return the correct contract object wrapped in prose or a
# ```json fence. Measured: that alone cost one full extra attempt on every run.
# Parse bare first, then a fenced block, then the last balanced top-level object.
function ConvertTo-ContractObject([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }

    try { return ($Text | ConvertFrom-Json -ErrorAction Stop) } catch { }

    $candidates = [System.Collections.Generic.List[string]]::new()
    foreach ($m in [regex]::Matches($Text, '(?s)```(?:json)?\s*(\{.*?\})\s*```')) {
        $candidates.Add($m.Groups[1].Value)
    }

    # Brace scan, string- and escape-aware so braces inside values do not fool it.
    $depth = 0; $start = -1; $inStr = $false; $esc = $false
    for ($i = 0; $i -lt $Text.Length; $i++) {
        $ch = $Text[$i]
        if ($inStr) {
            if ($esc) { $esc = $false }
            elseif ($ch -eq '\') { $esc = $true }
            elseif ($ch -eq '"') { $inStr = $false }
            continue
        }
        if ($ch -eq '"') { $inStr = $true; continue }
        if ($ch -eq '{') { if ($depth -eq 0) { $start = $i }; $depth++; continue }
        if ($ch -eq '}') {
            $depth--
            if ($depth -eq 0 -and $start -ge 0) {
                $candidates.Add($Text.Substring($start, $i - $start + 1))
                $start = -1
            }
            if ($depth -lt 0) { $depth = 0 }
        }
    }

    for ($k = $candidates.Count - 1; $k -ge 0; $k--) {
        try {
            $obj = $candidates[$k] | ConvertFrom-Json -ErrorAction Stop
            if ($null -ne $obj.PSObject.Properties['status']) { return $obj }
        }
        catch { }
    }
    return $null
}

# --- failure classification --------------------------------------------------
# transient : retry as-is with an escalated budget, no contract complaint
# hard      : stop now, retrying cannot help
# contract  : the model really did violate the output contract; feed the defect back
function Get-FailureClass([string]$Text, $Status) {
    $t = ([string]$Text).ToLowerInvariant()
    $code = 0
    if ($null -ne $Status) { [void][int]::TryParse([string]$Status, [ref]$code) }

    $hardPatterns = @(
        'no available channel', 'unknown option', 'unrecognized option',
        'invalid api key', 'invalid_api_key', 'authentication_error', 'unauthorized',
        'permission_error', 'permission denied', 'model not found',
        'does not exist', 'insufficient balance', 'insufficient quota',
        'quota exceeded', 'account is not authorized'
    )
    foreach ($p in $hardPatterns) { if ($t.Contains($p)) { return 'hard' } }
    if ($code -in @(400, 401, 403, 404, 422)) { return 'hard' }

    $transientPatterns = @(
        'overloaded', 'rate limit', 'rate_limit', 'timeout', 'timed out',
        'temporarily', 'try again', 'server-side issue', 'connection',
        'socket', 'econnreset', 'bad gateway', 'service unavailable',
        'budget', 'budget_exhausted', 'error_max_budget_usd'
    )
    foreach ($p in $transientPatterns) { if ($t.Contains($p)) { return 'transient' } }
    if ($code -in @(408, 409, 425, 429, 500, 502, 503, 504, 529)) { return 'transient' }
    return 'transient'
}

# --- attempt loop ------------------------------------------------------------
$budgetMultipliers = @(1.0, 1.5, 2.0, 2.5)
$final = $null
$lastClass = 'contract'
$lastError = 'No attempt completed.'
$contractFeedback = ''

Save-State 'running' $null

for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    $mult = $budgetMultipliers[[Math]::Min($attempt - 1, $budgetMultipliers.Count - 1)]
    $budget = [Math]::Round(([decimal]$MaxBudgetUsd * [decimal]$mult), 2)
    if ($budget -lt 0.05) { $budget = 0.05 }
    $rawPath = Join-Path $runDir ("attempt-{0}.raw.txt" -f ($resumedFrom + $attempt))

    $prompt = @"
Execute the following task now.
MODE: $Mode
TARGET ROOTS: $($roots | ConvertTo-Json -Compress)
TASK: $Task
ACCEPTANCE CRITERIA: $($script:criteria | ConvertTo-Json -Compress)
PREVIOUS RESULT DEFECT: $contractFeedback
For ReadOnly mode, never modify, run installers, download, delete, or copy files. For Implement mode, make only necessary reversible changes inside the target roots.
"@

    Write-Progress-Line "attempt=$attempt/$MaxAttempts mode=$Mode budget=$budget timeout=${TimeoutSeconds}s run=$RunId"

    $cliArgs = @(
        '--bare', '-p',
        '--model', $Model,
        '--effort', 'high',
        '--no-session-persistence',
        '--disable-slash-commands',
        '--permission-mode', 'auto',
        "--allowed-tools=$toolList",
        '--max-budget-usd', ([string]$budget),
        '--output-format', 'json',
        '--system-prompt', $systemPrompt,
        $prompt
    )

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $class = $null
    $errText = ''
    $result = $null
    $run = $null

    # Every attempt body is self-contained: an exception here must never escape
    # and rob the caller of its JSON document.
    try {
        $run = Invoke-ClaudeCli -Arguments $cliArgs -TimeoutMs ($TimeoutSeconds * 1000)
    }
    catch {
        $class = 'transient'
        $errText = "Process launch failed: $($_.Exception.Message)"
    }
    $sw.Stop()

    if ($null -ne $run) {
        # Guarded end to end: an unexpected envelope shape must never escape and
        # rob the caller of its JSON document.
        try {
            $body = "=== attempt $($resumedFrom + $attempt) ===`nexit=$($run.exitCode) timedOut=$($run.timedOut) elapsed_s=$([Math]::Round($sw.Elapsed.TotalSeconds,1)) budget=$budget`n--- stdout ---`n$($run.stdout)`n--- stderr ---`n$($run.stderr)`n"
            Set-Content -LiteralPath $rawPath -Value $body -Encoding UTF8

            if ($run.timedOut) {
                $class = 'transient'
                $errText = "Attempt exceeded ${TimeoutSeconds}s and was killed."
            }
            else {
                $cli = $null
                try { $cli = $run.stdout | ConvertFrom-Json -ErrorAction Stop } catch { $cli = $null }

                if ($null -eq $cli) {
                    $probe = "$($run.stdout)`n$($run.stderr)"
                    $class = Get-FailureClass $probe $null
                    if ($run.exitCode -eq 0) { $class = 'contract' }
                    $errText = "CLI produced no parseable envelope (exit $($run.exitCode))."
                }
                elseif ([bool](Get-Prop $cli 'is_error' $false) -or $run.exitCode -ne 0) {
                    $status = Get-Prop $cli 'api_error_status' $null
                    # Budget exhaustion supplies no result text; the only signal
                    # lives in subtype/terminal_reason, so both must be classified.
                    $msg = [string](Get-Prop $cli 'result' '')
                    $reason = [string](Get-Prop $cli 'terminal_reason' '')
                    $subtype = [string](Get-Prop $cli 'subtype' '')
                    $class = Get-FailureClass "$msg`n$reason`n$subtype`n$($run.stderr)" $status
                    $errText = "Provider error (exit $($run.exitCode), api_status=$status, terminal_reason=$reason, subtype=$subtype): $msg"
                }
                else {
                    $result = ConvertTo-ContractObject ([string](Get-Prop $cli 'result' ''))
                    if ($null -eq $result) {
                        $class = 'contract'
                        $errText = 'Final response was not the required JSON contract.'
                        $contractFeedback = 'Your last reply was not parseable JSON. Reply with the exact contract object and nothing else.'
                    }
                    else {
                        $required = @('status', 'completed_criteria', 'verification', 'remaining_work', 'next_action')
                        $missing = @($required | Where-Object { $null -eq $result.PSObject.Properties[$_] })
                        if ($missing.Count -gt 0) {
                            $class = 'contract'
                            $errText = 'Final JSON omitted required fields: ' + ($missing -join ', ')
                            $contractFeedback = "$errText. Read remaining artifacts and return the exact contract."
                        }
                        else {
                            $expected = @($script:criteria.id)
                            $actual = @($result.completed_criteria)
                            $unmet = @($expected | Where-Object { $_ -notin $actual })
                            $statusText = [string]$result.status

                            # A blocked verdict backed by evidence is a legitimate terminal
                            # state, not a contract violation. Retrying it only burns budget.
                            if ($statusText -eq 'blocked' -and @($result.verification).Count -gt 0) {
                                $class = 'blocked'
                                $errText = 'Model reported an evidenced blocker.'
                            }
                            elseif ($statusText -eq 'completed' -and $unmet.Count -eq 0 -and
                                    @($result.verification).Count -gt 0 -and @($result.remaining_work).Count -eq 0) {
                                $class = 'ok'
                            }
                            else {
                                $class = 'contract'
                                $errText = "Contract incomplete (status=$statusText, unmet=$($unmet -join ','))."
                                $contractFeedback = "Unfinished criteria: $($unmet -join ', '). Re-inspect the files, complete them, and return valid JSON with status=completed."
                            }
                        }
                    }
                }
            }
        }
        catch {
            $class = 'transient'
            $errText = "Runner failed while interpreting the attempt: $($_.Exception.Message)"
        }
    }

    $attemptLog.Add([pscustomobject]@{
        attempt = $resumedFrom + $attempt
        classification = $class
        budget_usd = $budget
        elapsed_s = [Math]::Round($sw.Elapsed.TotalSeconds, 1)
        exit_code = if ($null -ne $run) { $run.exitCode } else { $null }
        timed_out = if ($null -ne $run) { $run.timedOut } else { $false }
        error = $errText
        raw = $rawPath
    })
    $lastClass = $class
    $lastError = $errText
    Save-State 'running' $null
    Write-Progress-Line "attempt=$attempt class=$class elapsed=$([Math]::Round($sw.Elapsed.TotalSeconds,1))s"

    if ($class -eq 'ok') {
        $final = [pscustomobject]@{
            success = $true; status = 'completed'; attempts = ($resumedFrom + $attempt)
            model = $Model; mode = $Mode; result = $result
            run_dir = $runDir; handoff = (Get-Handoff 'none')
        }
        break
    }
    if ($class -eq 'blocked') {
        $final = [pscustomobject]@{
            success = $false; status = 'blocked'; attempts = ($resumedFrom + $attempt)
            model = $Model; mode = $Mode; result = $result
            error = 'Model reported an evidenced blocker; not retried.'
            run_dir = $runDir; handoff = (Get-Handoff 'blocked')
        }
        break
    }
    if ($class -eq 'hard') {
        $final = [pscustomobject]@{
            success = $false; status = 'failed'; failure_class = 'hard'
            attempts = ($resumedFrom + $attempt); model = $Model; mode = $Mode
            error = $errText; run_dir = $runDir; handoff = (Get-Handoff 'hard')
        }
        break
    }
    if ($class -eq 'transient' -and $attempt -lt $MaxAttempts) {
        $backoff = [Math]::Min(30, [Math]::Pow(2, $attempt))
        Write-Progress-Line "transient failure; backoff ${backoff}s then retry with a higher budget"
        Start-Sleep -Seconds $backoff
    }
}

if ($null -eq $final) {
    $final = [pscustomobject]@{
        success = $false; status = 'failed'; failure_class = $lastClass
        attempts = ($resumedFrom + $MaxAttempts); model = $Model; mode = $Mode
        error = "Exhausted $MaxAttempts attempts. Last: $lastError"
        run_dir = $runDir; handoff = (Get-Handoff $lastClass)
    }
}

$finalError = if ($null -ne $final.PSObject.Properties['error']) { [string]$final.error } else { $null }
Save-State $final.status $finalError
Complete-Run $final
