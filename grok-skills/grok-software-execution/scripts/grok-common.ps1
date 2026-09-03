# grok-common.ps1 — shared transport and classification for the grok-* runners.
# Dot-source with:  . (Join-Path $PSScriptRoot 'grok-common.ps1')
#
# Design rules these helpers exist to enforce:
#   * stdout carries the final JSON document and nothing else; progress -> stderr.
#   * the provider process is bounded, so a wedged child cannot hang the runner.
#   * provider credentials are set on the CHILD process only, never on the
#     caller's session (the old supervisor overwrote them and never restored).
#   * every envelope field is read defensively; the CLI envelope is not uniform.
#
# Deliberately does NOT set Set-StrictMode / $ErrorActionPreference: this file is
# dot-sourced, so doing so would mutate the caller's session — the same class of
# side effect this module exists to eliminate. Both callers set their own.

function Write-GrokProgress([string]$Tag, [string]$Message) {
    [Console]::Error.WriteLine("$Tag $Message")
}

# StrictMode makes a missing-property read fatal, and the CLI envelope varies:
# the budget-exhausted envelope carries no 'result' property at all.
function Get-Prop($Object, [string]$Name, $Default = $null) {
    if ($null -eq $Object) { return $Default }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) { return $Default }
    if ($null -eq $prop.Value) { return $Default }
    return $prop.Value
}

function New-GrokSlug([string]$Text) {
    $clean = ($Text -replace '[^A-Za-z0-9]+', '-').Trim('-').ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($clean)) { $clean = 'task' }
    if ($clean.Length -gt 32) { $clean = $clean.Substring(0, 32).Trim('-') }
    return $clean
}

# Resolves credentials + executable. Returns $null-free object or throws a plain
# message the caller turns into a hard-failure document.
function Resolve-GrokEndpoint {
    $settingsPath = Join-Path $HOME '.claude\settings.json'
    if (-not (Test-Path -LiteralPath $settingsPath)) {
        throw "Claude settings not found: $settingsPath"
    }
    $settings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
    $baseUrl = [string](Get-Prop $settings.env 'ANTHROPIC_BASE_URL' '')
    $token = [string](Get-Prop $settings.env 'ANTHROPIC_AUTH_TOKEN' '')
    if ([string]::IsNullOrWhiteSpace($baseUrl) -or [string]::IsNullOrWhiteSpace($token)) {
        throw 'Claude settings are missing provider credentials.'
    }
    $exe = Join-Path $env:APPDATA 'npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe'
    if (-not (Test-Path -LiteralPath $exe)) { throw "Missing Claude executable: $exe" }
    # Some Anthropic-compatible gateways omit their configured alias from /v1/models.
    # Preserve it so callers can treat the catalog as advisory for that exact alias.
    $configuredModels = @(
        [string](Get-Prop $settings.env 'ANTHROPIC_DEFAULT_OPUS_MODEL' ''),
        [string](Get-Prop $settings.env 'ANTHROPIC_DEFAULT_SONNET_MODEL' ''),
        [string](Get-Prop $settings.env 'ANTHROPIC_DEFAULT_HAIKU_MODEL' '')
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique
    return [pscustomobject]@{ BaseUrl = $baseUrl; Token = $token; Exe = $exe; ConfiguredModels = @($configuredModels) }
}

# Returns @{ Served = $true/$false; Models = @(...) }. Served is $true when the
# catalog is unreachable — an unreachable catalog is not proof the model is bad.
function Test-GrokModelServed($Endpoint, [string]$Model) {
    try {
        $catalog = Invoke-RestMethod -Uri "$($Endpoint.BaseUrl.TrimEnd('/'))/v1/models" -TimeoutSec 30 `
            -Headers @{ 'Authorization' = "Bearer $($Endpoint.Token)"; 'x-api-key' = $Endpoint.Token; 'anthropic-version' = '2023-06-01' }
        $ids = @($catalog.data.id)
        if ($ids.Count -eq 0) { return [pscustomobject]@{ Served = $true; Models = @(); Checked = $false } }
        return [pscustomobject]@{ Served = ($Model -in $ids); Models = ($ids | Sort-Object); Checked = $true }
    }
    catch {
        return [pscustomobject]@{ Served = $true; Models = @(); Checked = $false }
    }
}

# Bounded, deadlock-free child process. ArgumentList avoids quoting hell; async
# readers avoid pipe-buffer deadlock; WaitForExit(ms) bounds a wedged child.
function Invoke-GrokCli($Endpoint, [string[]]$Arguments, [string]$WorkingDirectory, [int]$TimeoutMs) {
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $Endpoint.Exe
    foreach ($a in $Arguments) { [void]$psi.ArgumentList.Add($a) }
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardInput = $true
    $psi.Environment['ANTHROPIC_API_KEY'] = $Endpoint.Token
    $psi.Environment['ANTHROPIC_BASE_URL'] = $Endpoint.BaseUrl

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

# transient : retry as-is with an escalated budget, no contract complaint
# hard      : stop now, retrying cannot help
function Get-GrokFailureClass([string]$Text, $Status) {
    $t = ([string]$Text).ToLowerInvariant()
    $code = 0
    if ($null -ne $Status) { [void][int]::TryParse([string]$Status, [ref]$code) }

    $hardPatterns = @(
        'unknown option', 'unrecognized option',
        'invalid api key', 'invalid_api_key', 'authentication_error', 'unauthorized',
        'permission_error', 'permission denied', 'model not found',
        'does not exist', 'insufficient balance', 'insufficient quota',
        'quota exceeded', 'account is not authorized'
    )
    foreach ($p in $hardPatterns) { if ($t.Contains($p)) { return 'hard' } }
    if ($code -in @(400, 401, 403, 404, 422)) { return 'hard' }

    $transientPatterns = @(
        'no available channel', 'overloaded', 'rate limit', 'rate_limit', 'timeout', 'timed out',
        'temporarily', 'try again', 'server-side issue', 'connection',
        'socket', 'econnreset', 'bad gateway', 'service unavailable',
        'budget', 'budget_exhausted', 'error_max_budget_usd'
    )
    foreach ($p in $transientPatterns) { if ($t.Contains($p)) { return 'transient' } }
    if ($code -in @(408, 409, 425, 429, 500, 502, 503, 504, 529)) { return 'transient' }
    return 'transient'
}

# Classifies a completed Invoke-GrokCli result at the transport level only.
# Returns @{ Class = ok|transient|hard; Reason = ...; Error = ...; Envelope; Payload }
# Class 'ok' means the provider call itself succeeded; the caller still has to
# judge whether the payload satisfies its own contract.
function Get-GrokCallOutcome($Run) {
    if ($Run.timedOut) {
        return [pscustomobject]@{ Class = 'transient'; Reason = 'timeout'; Error = $Run.stderr; Envelope = $null; Payload = '' }
    }
    $cli = $null
    try { $cli = $Run.stdout | ConvertFrom-Json -ErrorAction Stop } catch { $cli = $null }

    if ($null -eq $cli) {
        $class = Get-GrokFailureClass "$($Run.stdout)`n$($Run.stderr)" $null
        return [pscustomobject]@{
            Class = $class; Reason = 'no_envelope'; Envelope = $null; Payload = ''
            Error = "CLI produced no parseable envelope (exit $($Run.exitCode))."
        }
    }
    if ([bool](Get-Prop $cli 'is_error' $false) -or $Run.exitCode -ne 0) {
        $status = Get-Prop $cli 'api_error_status' $null
        # Budget exhaustion supplies no result text; the signal is in
        # subtype/terminal_reason, so both must reach the classifier.
        $msg = [string](Get-Prop $cli 'result' '')
        $reason = [string](Get-Prop $cli 'terminal_reason' '')
        $subtype = [string](Get-Prop $cli 'subtype' '')
        $class = Get-GrokFailureClass "$msg`n$reason`n$subtype`n$($Run.stderr)" $status

        # Budget exhaustion is deterministic, not flaky: the only useful response
        # is a bigger ceiling. Name it so the caller can say so out loud instead
        # of reporting an empty provider message.
        if ($reason -eq 'budget_exhausted' -or $subtype -eq 'error_max_budget_usd') {
            return [pscustomobject]@{
                Class = 'transient'; Reason = 'budget_exhausted'; Envelope = $cli; Payload = ''
                Error = 'Budget exhausted before the task finished.'
            }
        }
        return [pscustomobject]@{
            Class = $class; Reason = 'provider_error'; Envelope = $cli; Payload = $msg
            Error = "Provider error (exit $($Run.exitCode), api_status=$status, terminal_reason=$reason, subtype=$subtype): $msg"
        }
    }
    return [pscustomobject]@{
        Class = 'ok'; Reason = 'ok'; Envelope = $cli; Payload = [string](Get-Prop $cli 'result' ''); Error = ''
    }
}

# Models routinely return the correct contract object wrapped in prose or a
# ```json fence. Measured: that alone cost one full extra attempt on every run.
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

# Escalating budget: a budget-exhausted retry at the same ceiling fails identically.
# The ladder must keep climbing — measured: a ladder that flat-lines at 2.5x spends
# four full attempts failing at ceilings that could never cover the task.
function Get-GrokAttemptBudget([decimal]$Base, [int]$Attempt) {
    $mult = @(1.0, 1.5, 2.0, 2.5, 3.5, 5.0)
    $m = $mult[[Math]::Min($Attempt - 1, $mult.Count - 1)]
    $b = [Math]::Round(([decimal]$Base * [decimal]$m), 2)
    if ($b -lt 0.05) { $b = 0.05 }
    return $b
}
