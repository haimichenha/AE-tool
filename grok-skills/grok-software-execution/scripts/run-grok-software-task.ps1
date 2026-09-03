[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Task,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string[]]$TargetPath,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string[]]$AcceptanceCriteria,
    [ValidateSet('ReadOnly', 'Implement')][string]$Mode = 'ReadOnly',
    [ValidateRange(0, 6)][int]$MaxRetries = 3,
    [ValidateRange(10, 400)][int]$MaxEvidenceFiles = 120,
    [ValidateRange(0.05, 20.00)][decimal]$MaxBudgetUsd = 0.75,
    [string]$Model = 'claude-sonnet-4-6',
    [ValidateRange(30, 3600)][int]$TimeoutSeconds = 420,
    [string]$RunId,
    [switch]$SkipModelPreflight
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'grok-common.ps1')

$TAG = 'GROK_SOFTWARE'
function Say([string]$Message) { Write-GrokProgress $TAG $Message }

function Stop-Execution([string]$Message) {
    throw "grok-software-execution: $Message"
}

# ---------------------------------------------------------------- run directory
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = '{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), (New-GrokSlug $Task)
}
$runDir = Join-Path $HOME ".claude\grok-runs\$RunId"
if (-not (Test-Path -LiteralPath $runDir)) { [void](New-Item -ItemType Directory -Path $runDir -Force) }
$statePath = Join-Path $runDir 'state.json'
$ledger = [System.Collections.Generic.List[object]]::new()

function Save-State([string]$Status, $Error_, $Result) {
    $doc = [pscustomobject]@{
        run_id     = $RunId
        tool       = 'run-grok-software-task'
        status     = $Status
        error      = $Error_
        task       = $Task
        mode       = $Mode
        model      = $Model
        targets    = @($TargetPath)
        criteria   = @($AcceptanceCriteria)
        updated_at = (Get-Date).ToString('o')
        attempts   = @($ledger)
        last_result = $Result
    }
    $doc | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $statePath -Encoding UTF8
}

# stdout must carry the final JSON document and nothing else.
function Complete-Run($Document) {
    $Document | ConvertTo-Json -Depth 16
    exit 0
}

function Get-RawAttemptFiles {
    @(Get-ChildItem -LiteralPath $runDir -Filter 'attempt-*.raw.txt' -ErrorAction SilentlyContinue |
        ForEach-Object { $_.FullName })
}

function New-Failure([string]$Class, [string]$Message, [int]$Attempts, $LastResult) {
    Save-State 'failed' $Message $LastResult
    return [pscustomobject]@{
        success     = $false
        status      = 'failed'
        class       = $Class
        attempts    = $Attempts
        model       = $Model
        mode        = $Mode
        run_dir     = $runDir
        error       = $Message
        last_result = $LastResult
        handoff     = [pscustomobject]@{
            run_dir      = $runDir
            state_file   = $statePath
            raw_attempts = Get-RawAttemptFiles
            resume_with  = "-RunId $RunId"
        }
    }
}

Say "run_dir=$runDir mode=$Mode"

# ---------------------------------------------------------------- helpers kept from the original
function Get-SafeTextPreview([System.IO.FileInfo]$File, [string]$Extension) {
    $textExtensions = @('.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.ini', '.cfg', '.ps1', '.py', '.js', '.ts', '.cs', '.csv')
    if ($Extension -notin $textExtensions -or $File.Length -gt 16384) { return $null }
    try {
        $value = [IO.File]::ReadAllText($File.FullName)
        if ($value.Length -gt 2000) { return $value.Substring(0, 2000) }
        return $value
    }
    catch { return $null }
}

function Resolve-OperationPath([string]$RelativePath, [object[]]$Roots) {
    if ([string]::IsNullOrWhiteSpace($RelativePath) -or [IO.Path]::IsPathRooted($RelativePath)) {
        Stop-Execution "Operation path must be a non-empty relative path: $RelativePath"
    }
    foreach ($root in $Roots) {
        if ($root.kind -ne 'directory') { continue }
        $base = [IO.Path]::GetFullPath([string]$root.path).TrimEnd([IO.Path]::DirectorySeparatorChar)
        $candidate = [IO.Path]::GetFullPath((Join-Path $base $RelativePath))
        if ($candidate.StartsWith($base + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            return $candidate
        }
    }
    Stop-Execution "Operation path escapes the target roots: $RelativePath"
}

function Invoke-OperationManifest([object]$Result, [object[]]$Roots) {
    if ($null -eq $Result.PSObject.Properties['operations'] -or @($Result.operations).Count -eq 0) {
        return [pscustomobject]@{ valid = $false; reason = 'ACTION phase did not provide operations.'; applied = @() }
    }
    $applied = [System.Collections.Generic.List[object]]::new()
    foreach ($operation in @($Result.operations)) {
        if ($null -eq $operation -or $null -eq $operation.PSObject.Properties['kind'] -or $null -eq $operation.PSObject.Properties['path']) {
            return [pscustomobject]@{ valid = $false; reason = 'An operation is missing kind or path.'; applied = @($applied) }
        }
        $kind = [string]$operation.kind
        $target = Resolve-OperationPath -RelativePath ([string]$operation.path) -Roots $Roots
        switch ($kind) {
            'mkdir' {
                [void](New-Item -ItemType Directory -Path $target -Force)
                $applied.Add([pscustomobject]@{ kind = $kind; path = $target; verification = 'directory exists' })
            }
            'write_text' {
                if ($null -eq $operation.PSObject.Properties['content']) {
                    return [pscustomobject]@{ valid = $false; reason = 'write_text is missing content.'; applied = @($applied) }
                }
                $overwrite = $false
                if ($null -ne $operation.PSObject.Properties['overwrite']) { $overwrite = [bool]$operation.overwrite }
                if ((Test-Path -LiteralPath $target) -and -not $overwrite) {
                    return [pscustomobject]@{ valid = $false; reason = "write_text refuses to overwrite existing file: $target"; applied = @($applied) }
                }
                $parent = Split-Path -Parent $target
                [void](New-Item -ItemType Directory -Path $parent -Force)
                [IO.File]::WriteAllText($target, [string]$operation.content, [Text.UTF8Encoding]::new($false))
                $applied.Add([pscustomobject]@{ kind = $kind; path = $target; verification = 'UTF-8 text written' })
            }
            'replace_text' {
                if ($null -eq $operation.PSObject.Properties['find'] -or $null -eq $operation.PSObject.Properties['replace']) {
                    return [pscustomobject]@{ valid = $false; reason = 'replace_text is missing find or replace.'; applied = @($applied) }
                }
                if (-not (Test-Path -LiteralPath $target)) {
                    return [pscustomobject]@{ valid = $false; reason = "replace_text target is missing: $target"; applied = @($applied) }
                }
                $content = [IO.File]::ReadAllText($target)
                $find = [string]$operation.find
                $count = ([regex]::Matches($content, [regex]::Escape($find))).Count
                $expected = 1
                if ($null -ne $operation.PSObject.Properties['expected_matches']) { $expected = [int]$operation.expected_matches }
                if ($count -ne $expected) {
                    return [pscustomobject]@{ valid = $false; reason = "replace_text expected $expected matches but found ${count}: $target"; applied = @($applied) }
                }
                [IO.File]::WriteAllText($target, $content.Replace($find, [string]$operation.replace), [Text.UTF8Encoding]::new($false))
                $applied.Add([pscustomobject]@{ kind = $kind; path = $target; verification = "replaced $count exact match(es)" })
            }
            default {
                return [pscustomobject]@{ valid = $false; reason = "Unsupported operation kind: $kind"; applied = @($applied) }
            }
        }
    }
    return [pscustomobject]@{ valid = $true; reason = ''; applied = @($applied) }
}

function Get-EvidencePacket([string[]]$Paths, [int]$MaxFiles) {
    $roots = [System.Collections.Generic.List[object]]::new()
    $files = [System.Collections.Generic.List[object]]::new()
    $extensionCounts = @{}
    $fileId = 0
    $rootId = 0

    foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path)) {
            Stop-Execution "Target path does not exist: $path"
        }
        $item = Get-Item -LiteralPath $path -Force
        $rootId++
        $roots.Add([pscustomobject]@{
            id = "R$rootId"
            path = $item.FullName
            kind = if ($item.PSIsContainer) { 'directory' } else { 'file' }
            last_write_utc = $item.LastWriteTimeUtc.ToString('o')
        })

        $candidates = if ($item.PSIsContainer) {
            Get-ChildItem -LiteralPath $item.FullName -File -Recurse -Force -ErrorAction SilentlyContinue | Sort-Object LastWriteTimeUtc -Descending
        } else { @($item) }

        foreach ($file in $candidates) {
            $extension = if ([string]::IsNullOrWhiteSpace($file.Extension)) { '[none]' } else { $file.Extension.ToLowerInvariant() }
            if ($extensionCounts.ContainsKey($extension)) { $extensionCounts[$extension]++ } else { $extensionCounts[$extension] = 1 }
            if ($files.Count -ge $MaxFiles) { continue }
            $fileId++
            $files.Add([pscustomobject]@{
                id = "F$fileId"
                path = $file.FullName
                extension = $extension
                bytes = [int64]$file.Length
                last_write_utc = $file.LastWriteTimeUtc.ToString('o')
                text_preview = Get-SafeTextPreview -File $file -Extension $extension
            })
        }
    }

    [pscustomobject]@{
        generated_at_utc = [DateTime]::UtcNow.ToString('o')
        roots = @($roots)
        sampled_files = @($files)
        extension_counts = $extensionCounts
        sample_limit = $MaxFiles
    }
}

# structured_output is authoritative when the CLI supplies it. Otherwise the
# payload is free text that usually contains the contract object wrapped in
# prose or a ```json fence, which ConvertTo-ContractObject digs out.
function Get-StructuredResult([object]$Envelope, [string]$Payload) {
    $structured = Get-Prop $Envelope 'structured_output' $null
    if ($null -ne $structured) { return $structured }
    return (ConvertTo-ContractObject $Payload)
}

function Test-StructuredResult([object]$Result, [string[]]$EvidenceIds, [string[]]$CriterionIds) {
    if ($null -eq $Result) { return [pscustomobject]@{ valid = $false; reason = 'The model result was not valid JSON.' } }
    foreach ($name in @('status', 'verified_evidence', 'actions_taken', 'acceptance_results', 'remaining_work', 'next_action')) {
        if ($null -eq $Result.PSObject.Properties[$name]) {
            return [pscustomobject]@{ valid = $false; reason = "Missing required field: $name" }
        }
    }

    $validEvidence = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($id in $EvidenceIds) { [void]$validEvidence.Add($id) }
    foreach ($entry in @($Result.verified_evidence)) {
        if ($null -eq $entry -or $null -eq $entry.PSObject.Properties['id']) {
            return [pscustomobject]@{ valid = $false; reason = 'verified_evidence entry is missing id.' }
        }
        if (-not $validEvidence.Contains([string]$entry.id)) {
            return [pscustomobject]@{ valid = $false; reason = "Unknown evidence id in verified_evidence: $($entry.id)" }
        }
    }

    $seenCriteria = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($entry in @($Result.acceptance_results)) {
        if ($null -eq $entry -or $null -eq $entry.PSObject.Properties['criterion_id'] -or $null -eq $entry.PSObject.Properties['evidence_ids']) {
            return [pscustomobject]@{ valid = $false; reason = 'acceptance_results entry is missing required fields.' }
        }
        $criterionId = [string]$entry.criterion_id
        if ($CriterionIds -notcontains $criterionId) {
            return [pscustomobject]@{ valid = $false; reason = "Unknown acceptance criterion id: $criterionId" }
        }
        [void]$seenCriteria.Add($criterionId)
        foreach ($evidenceId in @($entry.evidence_ids)) {
            if (-not $validEvidence.Contains([string]$evidenceId)) {
                return [pscustomobject]@{ valid = $false; reason = "Unknown evidence id in acceptance result: $evidenceId" }
            }
        }
    }

    if ([string]$Result.status -eq 'completed') {
        foreach ($criterionId in $CriterionIds) {
            if (-not $seenCriteria.Contains($criterionId)) {
                return [pscustomobject]@{ valid = $false; reason = "Completed result omitted criterion: $criterionId" }
            }
        }
        foreach ($entry in @($Result.acceptance_results)) {
            if ([string]$entry.verdict -ne 'passed') {
                return [pscustomobject]@{ valid = $false; reason = "Completed result contains a non-passed criterion: $($entry.criterion_id)" }
            }
        }
        if (@($Result.remaining_work).Count -gt 0) {
            return [pscustomobject]@{ valid = $false; reason = 'Completed result still has remaining work.' }
        }
    }

    return [pscustomobject]@{ valid = $true; reason = '' }
}

# ---------------------------------------------------------------- endpoint
try { $endpoint = Resolve-GrokEndpoint }
catch { Complete-Run (New-Failure 'hard' $_.Exception.Message 0 $null) }

if (-not $SkipModelPreflight) {
    $probe = Test-GrokModelServed $endpoint $Model
    $configuredAlias = $Model -in @($endpoint.ConfiguredModels)
    if ($probe.Checked -and -not $probe.Served -and -not $configuredAlias) {
        # Fails in ~2s instead of burning a full attempt cycle on a dead route.
        $doc = New-Failure 'hard' "Model '$Model' is not served by this endpoint." 0 $null
        $doc | Add-Member -NotePropertyName 'available_models' -NotePropertyValue @($probe.Models)
        Complete-Run $doc
    }
    if ($probe.Checked -and -not $probe.Served -and $configuredAlias) {
        Say "preflight catalog omits configured alias model=$Model; proceeding to bounded actual call"
    }
    else {
        Say "preflight model=$Model served=$($probe.Served) checked=$($probe.Checked)"
    }
}

$timeoutMs = $TimeoutSeconds * 1000

# ---------------------------------------------------------------- evidence + contract
# Every remaining failure mode below must still leave a JSON document on stdout,
# so the whole body runs inside one guard: Stop-Execution and any unexpected
# runtime error become a classified failure document instead of a bare throw.
$attempt = 0
$retryReason = ''
$lastTransientError = ''
$lastClass = 'contract'
$lastResult = $null
$final = $null

try {
    $packet = Get-EvidencePacket -Paths $TargetPath -MaxFiles $MaxEvidenceFiles
    $evidenceIds = @($packet.roots.id) + @($packet.sampled_files.id)
    $criteria = for ($index = 0; $index -lt $AcceptanceCriteria.Count; $index++) {
        [pscustomobject]@{ id = "A$($index + 1)"; text = $AcceptanceCriteria[$index] }
    }
    $criterionIds = @($criteria.id)
    Say "evidence roots=$($packet.roots.Count) files=$($packet.sampled_files.Count) criteria=$($criterionIds.Count)"

    $readOnlyTools = 'Read,Glob,Grep,LS'
    $postActionVerification = $false
    $actionReport = $null
    $systemPrompt = @"
You are a Chinese software execution agent controlled by an evidence gate.
Complete the task rather than acknowledging it or asking the user to choose options.
Use only supplied evidence IDs for verified claims. Missing evidence must be called out as needs_evidence or blocked.
Keep working through inspect, act, verify, and remaining work until every acceptance criterion is passed or a real blocker is documented.
Return only this exact JSON shape; do not replace any array with a string. In ACTION phase, add operations as an array of write_text, replace_text, or mkdir objects. Do not use tools directly; the controller applies operations:
{"status":"completed|blocked|needs_evidence","verified_evidence":[{"id":"R1","claim":"fact"}],"actions_taken":["action"],"operations":[{"kind":"write_text","path":"relative.txt","content":"text"}],"acceptance_results":[{"criterion_id":"A1","verdict":"passed|failed|blocked","evidence_ids":["R1"],"detail":"result"}],"remaining_work":[],"next_action":"action"}
Never switch models. Never claim completion if any criterion is unverified, failed, blocked, or still remaining.
"@

    while ($attempt -le $MaxRetries) {
        $attempt++
        $phase = if ($Mode -eq 'Implement' -and -not $postActionVerification) { 'ACTION' } else { 'VERIFY' }
        # The model emits a constrained action manifest; the host applies it. This
        # avoids unreliable direct tool calls while preserving the same model.
        $currentToolList = $readOnlyTools
        $previousAction = if ($null -ne $actionReport) { $actionReport | ConvertTo-Json -Depth 12 -Compress } else { '' }
        $taskPrompt = @"
Execute this software task in Chinese.

MODE: $Mode
PHASE: $phase
TASK:
$Task

ACCEPTANCE CRITERIA:
$($criteria | ConvertTo-Json -Depth 4 -Compress)

EVIDENCE PACKET:
$($packet | ConvertTo-Json -Depth 8 -Compress)

PREVIOUS VALIDATION FAILURE:
$retryReason

PREVIOUS ACTION REPORT:
$previousAction

For VERIFY phase and ReadOnly mode, do not modify, run, install, download, delete, or copy files.
For ACTION phase, emit only the constrained operations manifest. The controller applies it inside the supplied target roots, refreshes evidence, and requires a separate verification phase before completion.
"@

        # A budget-exhausted retry at the same ceiling fails identically, so the
        # ceiling climbs with the attempt number.
        $budget = Get-GrokAttemptBudget $MaxBudgetUsd $attempt
        # Use the inline form because the CLI's variable-length --add-dir form
        # would otherwise consume the final positional task prompt on Windows.
        $claudeArgs = @('--bare', '-p')
        foreach ($root in @($packet.roots)) { $claudeArgs += "--add-dir=$($root.path)" }
        $claudeArgs += @('--model', $Model, '--effort', 'high', '--no-session-persistence',
            '--disable-slash-commands', '--permission-mode', 'auto', "--allowed-tools=$currentToolList",
            '--max-budget-usd', ([string]$budget), '--output-format', 'json',
            '--system-prompt', $systemPrompt)
        $claudeArgs += $taskPrompt

        $workingDirectory = if ($packet.roots[0].kind -eq 'directory') { $packet.roots[0].path } else { Split-Path -Parent $packet.roots[0].path }
        Say "attempt=$attempt/$($MaxRetries + 1) phase=$phase budget=$budget"

        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        # Self-contained attempt body: an escaping exception here used to kill the
        # runner outright and print no JSON at all.
        try {
            $run = Invoke-GrokCli $endpoint $claudeArgs $workingDirectory $timeoutMs
            $outcome = Get-GrokCallOutcome $run
            $raw = [regex]::Replace("$($run.stdout)`n$($run.stderr)", '(?i)(sk|bearer|token)[-_a-z0-9.]{12,}', '$1-[REDACTED]')
            $rawPath = Join-Path $runDir ("attempt-{0}.raw.txt" -f $attempt)
            @(
                "attempt=$attempt phase=$phase budget=$budget model=$Model mode=$Mode",
                "workdir=$workingDirectory",
                "exit=$($run.exitCode) timedOut=$($run.timedOut) class=$($outcome.Class) reason=$($outcome.Reason) elapsed=$([Math]::Round($sw.Elapsed.TotalSeconds,1))s",
                '--- raw ---', $raw
            ) -join "`n" | Set-Content -LiteralPath $rawPath -Encoding UTF8
        }
        catch {
            $lastClass = 'transient'
            $lastTransientError = "Runner failed while invoking the provider: $($_.Exception.Message)"
            $ledger.Add([pscustomobject]@{ attempt = $attempt; phase = $phase; class = 'transient'; reason = 'runner_exception'; budget = $budget; seconds = [Math]::Round($sw.Elapsed.TotalSeconds, 1); error = $lastTransientError })
            Say "attempt=$attempt runner exception: $($_.Exception.Message)"
            Start-Sleep -Seconds ([Math]::Min(2 * $attempt, 10))
            continue
        }

        $seconds = [Math]::Round($sw.Elapsed.TotalSeconds, 1)
        $err = $outcome.Error
        if ($outcome.Reason -eq 'budget_exhausted') {
            $err = "Budget exhausted at $budget USD (attempt $attempt). Raise -MaxBudgetUsd."
        }
        $ledger.Add([pscustomobject]@{ attempt = $attempt; phase = $phase; class = $outcome.Class; reason = $outcome.Reason; budget = $budget; seconds = $seconds; error = $err })

        if ($outcome.Class -eq 'hard') {
            Say "attempt=$attempt hard failure: $err"
            Complete-Run (New-Failure 'hard' $err $attempt $lastResult)
        }
        if ($outcome.Class -eq 'transient') {
            # Transport failed. Feeding this back as PREVIOUS VALIDATION FAILURE
            # would tell the model it was wrong when the network was, so
            # $retryReason is deliberately left untouched.
            $lastClass = 'transient'
            $lastTransientError = $err
            Say "attempt=$attempt transient (${seconds}s): $err"
            Start-Sleep -Seconds ([Math]::Min(2 * $attempt, 10))
            continue
        }

        $result = Get-StructuredResult -Envelope $outcome.Envelope -Payload $outcome.Payload
        $lastResult = $result
        Save-State 'running' $null $lastResult

        if ($Mode -eq 'Implement' -and -not $postActionVerification -and $null -ne $result) {
            $manifest = Invoke-OperationManifest -Result $result -Roots @($packet.roots)
            if (-not $manifest.valid) {
                $lastClass = 'contract'
                $retryReason = $manifest.reason
                Say "attempt=$attempt manifest rejected: $($manifest.reason)"
                continue
            }
            $actionReport = [pscustomobject]@{ model_report = $result; host_actions = @($manifest.applied) }
            $packet = Get-EvidencePacket -Paths $TargetPath -MaxFiles $MaxEvidenceFiles
            $evidenceIds = @($packet.roots.id) + @($packet.sampled_files.id)
            $postActionVerification = $true
            $retryReason = 'Action manifest applied. Verify the refreshed evidence packet only; do not repeat the action.'
            Say "attempt=$attempt applied $($manifest.applied.Count) operation(s), moving to VERIFY"
            continue
        }

        $validation = Test-StructuredResult -Result $result -EvidenceIds $evidenceIds -CriterionIds $criterionIds
        if ($validation.valid) {
            $final = [pscustomobject]@{
                success  = ([string]$result.status -eq 'completed')
                status   = [string]$result.status
                class    = 'ok'
                attempts = $attempt
                model    = $Model
                mode     = $Mode
                run_dir  = $runDir
                cli_stop_reason = [string](Get-Prop $outcome.Envelope 'stop_reason' '')
                result   = $result
                handoff  = [pscustomobject]@{
                    run_dir     = $runDir
                    state_file  = $statePath
                    resume_with = "-RunId $RunId"
                }
            }
            Say "attempt=$attempt accepted in ${seconds}s (status=$($result.status))"
            break
        }
        # The provider call succeeded, so this is genuinely the model's contract
        # defect and is the one thing worth feeding back to it.
        $lastClass = 'contract'
        $retryReason = $validation.reason
        Say "attempt=$attempt contract violation: $($validation.reason)"
    }
}
catch {
    Complete-Run (New-Failure 'hard' "Runner aborted: $($_.Exception.Message)" $attempt $lastResult)
}

if ($null -eq $final) {
    $why = if ($lastClass -eq 'contract' -and -not [string]::IsNullOrWhiteSpace($retryReason)) { $retryReason } else { $lastTransientError }
    Complete-Run (New-Failure $lastClass "No acceptance-gated result after $attempt attempt(s): $why" $attempt $lastResult)
}

Save-State 'succeeded' $null $final.result
Complete-Run $final
