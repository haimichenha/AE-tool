[CmdletBinding()]
param(
    [Parameter(Mandatory)][string[]]$ArtifactPath,
    [Parameter(Mandatory)][string]$Objective,
    [ValidateRange(1,6)][int]$MaxAttemptsPerArtifact = 3,
    [ValidateRange(0.05,20.00)][decimal]$MaxBudgetUsd = 0.30,
    # Synthesis reasons over every accepted report at once, so it is a larger
    # workload than any single artifact read and needs its own ceiling. Measured:
    # reusing the per-artifact budget burned 4 attempts / 340s that could not
    # possibly have succeeded. 0 = derive from MaxBudgetUsd.
    [ValidateRange(0.00,40.00)][decimal]$SynthesisBudgetUsd = 0,
    [string]$Model = 'claude-sonnet-4-6',
    [ValidateRange(30,3600)][int]$TimeoutSeconds = 300,
    [string]$RunId,
    [switch]$SkipModelPreflight
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'grok-common.ps1')

$TAG = 'GROK_SUPERVISOR'
function Say([string]$Message) { Write-GrokProgress $TAG $Message }

# ---------------------------------------------------------------- run directory
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = '{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), (New-GrokSlug $Objective)
}
$runDir = Join-Path $HOME ".claude\grok-runs\$RunId"
if (-not (Test-Path -LiteralPath $runDir)) { [void](New-Item -ItemType Directory -Path $runDir -Force) }
$statePath = Join-Path $runDir 'state.json'
$ledger = [System.Collections.Generic.List[object]]::new()

function Save-State([string]$Status, $Error_, $Reports, [string]$Synthesis) {
    $doc = [pscustomobject]@{
        run_id     = $RunId
        tool       = 'supervise-grok-artifacts'
        status     = $Status
        error      = $Error_
        objective  = $Objective
        model      = $Model
        artifacts  = @($ArtifactPath)
        updated_at = (Get-Date).ToString('o')
        attempts   = @($ledger)
        reports    = @($Reports)
        synthesis  = $Synthesis
    }
    $doc | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $statePath -Encoding UTF8
}

# stdout must carry the final JSON document and nothing else.
function Complete-Run($Document) {
    $Document | ConvertTo-Json -Depth 14
    exit 0
}

function New-Failure([string]$Class, [string]$Message, $Reports, [string]$Synthesis) {
    Save-State 'failed' $Message $Reports $Synthesis
    return [pscustomobject]@{
        success   = $false
        status    = 'failed'
        class     = $Class
        error     = $Message
        model     = $Model
        run_dir   = $runDir
        reports   = @($Reports)
        synthesis = $Synthesis
        handoff   = [pscustomobject]@{
            run_dir      = $runDir
            state_file   = $statePath
            raw_attempts = @(Get-ChildItem -LiteralPath $runDir -Filter 'attempt-*.raw.txt' -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
            resume_with  = "-RunId $RunId"
        }
    }
}

Say "run_dir=$runDir"

# ---------------------------------------------------------------- endpoint
try { $endpoint = Resolve-GrokEndpoint }
catch { Complete-Run (New-Failure 'hard' $_.Exception.Message @() '') }

if (-not $SkipModelPreflight) {
    $probe = Test-GrokModelServed $endpoint $Model
    if ($probe.Checked -and -not $probe.Served) {
        # Fails in ~2s instead of burning a full attempt cycle on a dead route.
        $doc = New-Failure 'hard' "Model '$Model' is not served by this endpoint." @() ''
        $doc | Add-Member -NotePropertyName 'available_models' -NotePropertyValue @($probe.Models)
        Complete-Run $doc
    }
    Say "preflight model=$Model served=$($probe.Served) checked=$($probe.Checked)"
}

$timeoutMs = $TimeoutSeconds * 1000

function Invoke-Supervisor([string]$Label, [string]$System, [string]$Prompt, [string]$WorkDir, [int]$Attempt, [decimal]$BaseBudget) {
    $budget = Get-GrokAttemptBudget $BaseBudget $Attempt
    $cliArgs = @(
        '--bare', '-p',
        '--model', $Model,
        '--effort', 'high',
        '--no-session-persistence',
        '--disable-slash-commands',
        '--permission-mode', 'auto',
        '--allowed-tools=Read,Glob,Grep,LS',
        '--max-budget-usd', ([string]$budget),
        '--output-format', 'json',
        '--system-prompt', $System,
        $Prompt
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    # Every attempt body is self-contained: an escaping exception here would
    # leave the caller with a bare PowerShell error and no JSON at all.
    try {
        $run = Invoke-GrokCli $endpoint $cliArgs $WorkDir $timeoutMs
        $outcome = Get-GrokCallOutcome $run
        $rawPath = Join-Path $runDir ("attempt-{0}-{1}.raw.txt" -f $Label, $Attempt)
        @(
            "label=$Label attempt=$Attempt budget=$budget model=$Model",
            "workdir=$WorkDir",
            "exit=$($run.exitCode) timedOut=$($run.timedOut) class=$($outcome.Class) elapsed=$([Math]::Round($sw.Elapsed.TotalSeconds,1))s",
            '--- stdout ---', $run.stdout,
            '--- stderr ---', $run.stderr
        ) -join "`n" | Set-Content -LiteralPath $rawPath -Encoding UTF8
    }
    catch {
        return [pscustomobject]@{
            Class = 'transient'; Reason = 'runner_exception'; Payload = ''; Budget = $budget; Seconds = [Math]::Round($sw.Elapsed.TotalSeconds, 1)
            Error = "Supervisor failed while invoking the provider: $($_.Exception.Message)"
        }
    }
    # An empty provider message helps nobody; say what the ceiling was and what to raise.
    $err = $outcome.Error
    if ($outcome.Reason -eq 'budget_exhausted') {
        $err = "Budget exhausted at $budget USD (attempt $Attempt). Raise the base budget for this phase."
    }
    return [pscustomobject]@{
        Class   = $outcome.Class
        Reason  = $outcome.Reason
        Payload = $outcome.Payload
        Error   = $err
        Budget  = $budget
        Seconds = [Math]::Round($sw.Elapsed.TotalSeconds, 1)
    }
}

# ---------------------------------------------------------------- per artifact
$reports = [System.Collections.Generic.List[object]]::new()

foreach ($artifact in $ArtifactPath) {
    if (-not (Test-Path -LiteralPath $artifact)) {
        Say "artifact missing: $artifact"
        $reports.Add([pscustomobject]@{ path = $artifact; status = 'missing'; class = 'hard'; attempts = 0; report = ''; error = 'Artifact does not exist.' })
        continue
    }
    $full = (Get-Item -LiteralPath $artifact).FullName
    $name = Split-Path -Leaf $full
    $parent = Split-Path -Parent $full
    $label = New-GrokSlug $name

    $accepted = $false
    $last = ''
    $lastErr = ''
    $lastClass = 'contract'
    $used = 0

    for ($attempt = 1; $attempt -le $MaxAttemptsPerArtifact; $attempt++) {
        $used = $attempt
        Say "artifact=$name attempt=$attempt/$MaxAttemptsPerArtifact"

        $system = 'You are a Chinese evidence reader. Use Read on the exact requested file before answering. Do not give a plan, menu, or generic summary. State only facts present in the file and their implication for the stated objective.'
        # A transient failure must not be fed back as a contract complaint —
        # doing so tells the model it was wrong when the network was.
        $feedback = if ($lastClass -eq 'contract' -and -not [string]::IsNullOrWhiteSpace($last)) {
            "Previous insufficient report (fix the missing labels/facts): $last"
        } else { '' }
        $prompt = @"
Objective: $Objective
Exact artifact to read now: $full
Use a read-only tool to read this file. Then return Chinese text with exactly these labels:
PATH: the exact path
FACTS: at least two concrete facts from file content
IMPLICATION: what those facts mean for the objective
Do not inspect binaries, do not modify files, and do not ask for confirmation.
$feedback
"@

        $r = Invoke-Supervisor $label $system $prompt $parent $attempt $MaxBudgetUsd
        $ledger.Add([pscustomobject]@{
            artifact = $name; attempt = $attempt; class = $r.Class; reason = $r.Reason
            budget = $r.Budget; seconds = $r.Seconds; error = $r.Error
        })

        if ($r.Class -eq 'hard') {
            $lastClass = 'hard'; $lastErr = $r.Error
            Say "artifact=$name hard failure: $($r.Error)"
            break
        }
        if ($r.Class -eq 'transient') {
            $lastClass = 'transient'; $lastErr = $r.Error
            Say "artifact=$name transient ($($r.Seconds)s): $($r.Error)"
            Start-Sleep -Seconds ([Math]::Min(2 * $attempt, 10))
            continue
        }

        $last = $r.Payload
        $ok = ($last.Length -ge 120) -and $last.Contains($name) -and ($last -match 'FACTS:') -and ($last -match 'IMPLICATION:')
        if ($ok) {
            $accepted = $true
            Say "artifact=$name accepted in $($r.Seconds)s"
            break
        }
        $lastClass = 'contract'
        $lastErr = 'Report is missing required labels, the file name, or sufficient length.'
        Say "artifact=$name contract violation, retrying"
    }

    $reports.Add([pscustomobject]@{
        path     = $full
        status   = if ($accepted) { 'accepted' } else { 'insufficient' }
        class    = if ($accepted) { 'ok' } else { $lastClass }
        attempts = $used
        report   = $last
        error    = if ($accepted) { '' } else { $lastErr }
    })
    Save-State 'running' $null $reports ''
}

# ---------------------------------------------------------------- synthesis
$acceptedReports = @($reports | Where-Object { $_.status -eq 'accepted' })
$synthesis = ''
$synthClass = 'ok'
$synthErr = ''

if ($acceptedReports.Count -gt 0) {
    $synthBudget = if ($SynthesisBudgetUsd -gt 0) { $SynthesisBudgetUsd }
                   else { [Math]::Max([decimal]($MaxBudgetUsd * 3), [decimal]0.45) }
    Say "synthesis accepted=$($acceptedReports.Count)/$($reports.Count) budget=$synthBudget"
    $evidence = $acceptedReports | Select-Object path, report | ConvertTo-Json -Depth 5 -Compress
    $root = Split-Path -Parent $acceptedReports[0].path
    $system = 'You are a Chinese technical synthesizer. Use only supplied evidence reports. Do not invent facts, do not provide menus, and distinguish verified conclusions from missing evidence.'
    $prompt = "Objective: $Objective`nEvidence reports: $evidence`nProduce: verified cross-file conclusions; failed or unsupported paths; one safe next action."

    for ($attempt = 1; $attempt -le $MaxAttemptsPerArtifact; $attempt++) {
        $r = Invoke-Supervisor 'synthesis' $system $prompt $root $attempt $synthBudget
        $ledger.Add([pscustomobject]@{
            artifact = '(synthesis)'; attempt = $attempt; class = $r.Class; reason = $r.Reason
            budget = $r.Budget; seconds = $r.Seconds; error = $r.Error
        })
        if ($r.Class -eq 'ok' -and -not [string]::IsNullOrWhiteSpace($r.Payload)) {
            $synthesis = $r.Payload
            $synthClass = 'ok'
            Say "synthesis done in $($r.Seconds)s"
            break
        }
        $synthClass = if ($r.Class -eq 'ok') { 'contract' } else { $r.Class }
        $synthErr = if ($r.Class -eq 'ok') { 'Synthesis returned empty text.' } else { $r.Error }
        Say "synthesis $($synthClass): $synthErr"
        if ($synthClass -eq 'hard') { break }
        Start-Sleep -Seconds ([Math]::Min(2 * $attempt, 10))
    }
}

# ---------------------------------------------------------------- terminal
$failed = @($reports | Where-Object { $_.status -ne 'accepted' })
if ($failed.Count -gt 0) {
    $why = ($failed | ForEach-Object { "$(Split-Path -Leaf $_.path): $($_.error)" }) -join ' | '
    $cls = if (@($failed | Where-Object { $_.class -eq 'hard' }).Count -gt 0) { 'hard' } else { $failed[0].class }
    Complete-Run (New-Failure $cls "Unaccepted artifacts ($($failed.Count)/$($reports.Count)): $why" $reports $synthesis)
}
if ($acceptedReports.Count -gt 0 -and [string]::IsNullOrWhiteSpace($synthesis)) {
    Complete-Run (New-Failure $synthClass "Synthesis failed: $synthErr" $reports $synthesis)
}

Save-State 'succeeded' $null $reports $synthesis
Complete-Run ([pscustomobject]@{
    success   = $true
    status    = 'succeeded'
    class     = 'ok'
    model     = $Model
    run_dir   = $runDir
    objective = $Objective
    reports   = @($reports)
    synthesis = $synthesis
    stats     = [pscustomobject]@{
        artifacts     = $reports.Count
        accepted      = $acceptedReports.Count
        total_calls   = $ledger.Count
        max_attempts  = $MaxAttemptsPerArtifact
        base_budget   = $MaxBudgetUsd
    }
    handoff   = [pscustomobject]@{
        run_dir     = $runDir
        state_file  = $statePath
        resume_with = "-RunId $RunId"
    }
})
