[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Task,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string[]]$TargetPath,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string[]]$AcceptanceCriteria,
    [ValidateSet('ReadOnly', 'Implement')][string]$Mode = 'ReadOnly',
    [ValidateRange(0, 3)][int]$MaxRetries = 2,
    [ValidateRange(10, 400)][int]$MaxEvidenceFiles = 120,
    [ValidateRange(0.05, 5.00)][decimal]$MaxBudgetUsd = 0.75,
    [string]$Model = 'grok-4.6'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Stop-Execution([string]$Message) {
    throw "grok-software-execution: $Message"
}

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
        $base = [IO.Path]::GetFullPath([string]$root.path).TrimEnd('\\')
        $candidate = [IO.Path]::GetFullPath((Join-Path $base $RelativePath))
        if ($candidate.StartsWith($base + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            return $candidate
        }
    }
    Stop-Execution "Operation path escapes the target roots: $RelativePath"
}

function Apply-OperationManifest([object]$Result, [object[]]$Roots) {
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

function Get-StructuredResult([object]$CliResponse) {
    if ($null -ne $CliResponse.PSObject.Properties['structured_output'] -and $null -ne $CliResponse.structured_output) {
        return $CliResponse.structured_output
    }
    if ($null -ne $CliResponse.PSObject.Properties['result'] -and $CliResponse.result) {
        try { return ($CliResponse.result | ConvertFrom-Json -ErrorAction Stop) }
        catch { return $null }
    }
    return $null
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

$settingsPath = Join-Path $HOME '.claude\settings.json'
if (-not (Test-Path -LiteralPath $settingsPath)) { Stop-Execution "Missing Claude settings: $settingsPath" }
$settings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
$baseUrl = [string]$settings.env.ANTHROPIC_BASE_URL
$authToken = [string]$settings.env.ANTHROPIC_AUTH_TOKEN
if ([string]::IsNullOrWhiteSpace($baseUrl) -or [string]::IsNullOrWhiteSpace($authToken)) {
    Stop-Execution 'Claude settings must include ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN.'
}

$claudeCmd = Join-Path $env:APPDATA 'npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe'
if (-not (Test-Path -LiteralPath $claudeCmd)) { Stop-Execution "Missing Claude CLI command: $claudeCmd" }
$bridgePath = Join-Path $PSScriptRoot 'invoke-claude-json.py'
if (-not (Test-Path -LiteralPath $bridgePath)) { Stop-Execution "Missing CLI bridge: $bridgePath" }

$packet = Get-EvidencePacket -Paths $TargetPath -MaxFiles $MaxEvidenceFiles
$evidenceIds = @($packet.roots.id) + @($packet.sampled_files.id)
$criteria = for ($index = 0; $index -lt $AcceptanceCriteria.Count; $index++) {
    [pscustomobject]@{ id = "A$($index + 1)"; text = $AcceptanceCriteria[$index] }
}
$criterionIds = @($criteria.id)

$schema = @{
    type = 'object'; additionalProperties = $false
    required = @('status', 'verified_evidence', 'actions_taken', 'acceptance_results', 'remaining_work', 'next_action')
    properties = @{
        status = @{ type = 'string'; enum = @('completed', 'blocked', 'needs_evidence') }
        verified_evidence = @{ type = 'array'; items = @{
            type = 'object'; additionalProperties = $false; required = @('id', 'claim')
            properties = @{ id = @{ type = 'string' }; claim = @{ type = 'string' } }
        }}
        actions_taken = @{ type = 'array'; items = @{ type = 'string' } }
        acceptance_results = @{ type = 'array'; items = @{
            type = 'object'; additionalProperties = $false; required = @('criterion_id', 'verdict', 'evidence_ids', 'detail')
            properties = @{
                criterion_id = @{ type = 'string' }
                verdict = @{ type = 'string'; enum = @('passed', 'failed', 'blocked') }
                evidence_ids = @{ type = 'array'; items = @{ type = 'string' } }
                detail = @{ type = 'string' }
            }
        }}
        remaining_work = @{ type = 'array'; items = @{ type = 'string' } }
        next_action = @{ type = 'string' }
    }
} | ConvertTo-Json -Depth 12 -Compress

$readOnlyTools = 'Read,Glob,Grep,LS'
$implementTools = 'Bash,Read,Glob,Grep,LS,Write,Edit'
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

$previousApiKey = $env:ANTHROPIC_API_KEY
$previousBaseUrl = $env:ANTHROPIC_BASE_URL
$previousNativeArgumentPassing = $null
if (Get-Variable -Name PSNativeCommandArgumentPassing -ErrorAction SilentlyContinue) {
    $previousNativeArgumentPassing = $PSNativeCommandArgumentPassing
    $PSNativeCommandArgumentPassing = 'Standard'
}
$env:ANTHROPIC_API_KEY = $authToken
$env:ANTHROPIC_BASE_URL = $baseUrl
$attempt = 0
$retryReason = ''
$lastRawSummary = ''
$lastResult = $null
$final = $null

try {
    while ($attempt -le $MaxRetries) {
        $attempt++
        $phase = if ($Mode -eq 'Implement' -and -not $postActionVerification) { 'ACTION' } else { 'VERIFY' }
        # Grok emits a constrained action manifest; the host applies it. This
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

        # Use the inline form because the CLI's variable-length --add-dir form
        # would otherwise consume the final positional task prompt on Windows.
        $claudeArgs = @('--bare', '-p')
        foreach ($root in @($packet.roots)) { $claudeArgs += "--add-dir=$($root.path)" }
        $claudeArgs += @('--model', $Model, '--effort', 'high', '--no-session-persistence',
            '--disable-slash-commands', '--permission-mode', 'auto', "--allowed-tools=$currentToolList",
            '--max-budget-usd', ([string]$MaxBudgetUsd), '--output-format', 'json',
            '--system-prompt', $systemPrompt)
        $claudeArgs += $taskPrompt

        $workingDirectory = if ($packet.roots[0].kind -eq 'directory') { $packet.roots[0].path } else { Split-Path -Parent $packet.roots[0].path }
        Push-Location -LiteralPath $workingDirectory
        try {
            # A Python bridge preserves the long, JSON-bearing final prompt when
            # invoking the Windows .cmd launcher; PowerShell native argument passing does not.
            $requestPath = Join-Path $env:TEMP ("grok-software-execution-" + [guid]::NewGuid().ToString('N') + '.json')
            try {
                $request = [pscustomobject]@{ command = $claudeCmd; args = @($claudeArgs) }
                [IO.File]::WriteAllText($requestPath, ($request | ConvertTo-Json -Depth 6 -Compress), [Text.UTF8Encoding]::new($false))
                $bridgeRaw = & py -3.13 $bridgePath --request $requestPath
                $bridgeExit = $LASTEXITCODE
                if ($bridgeExit -ne 0) { Stop-Execution "CLI bridge exit code: $bridgeExit" }
                $bridge = ($bridgeRaw | Out-String | ConvertFrom-Json -ErrorAction Stop)
                $exitCode = [int]$bridge.returncode
                $raw = ([string]$bridge.stdout) + ([string]$bridge.stderr)
            }
            finally {
                if (Test-Path -LiteralPath $requestPath) { Remove-Item -LiteralPath $requestPath -Force }
            }
            $lastRawSummary = [regex]::Replace($raw, '(?i)(sk|bearer|token)[-_a-z0-9.]{12,}', '$1-[REDACTED]')
            if ($lastRawSummary.Length -gt 800) { $lastRawSummary = $lastRawSummary.Substring(0, 800) }
        }
        finally { Pop-Location }

        try { $cliResponse = $raw | ConvertFrom-Json -ErrorAction Stop }
        catch { $retryReason = "The CLI returned non-JSON output: $lastRawSummary"; continue }

        $result = Get-StructuredResult -CliResponse $cliResponse
        $lastResult = $result

        if ($Mode -eq 'Implement' -and -not $postActionVerification -and $null -ne $result) {
            $manifest = Apply-OperationManifest -Result $result -Roots @($packet.roots)
            if (-not $manifest.valid) {
                $retryReason = $manifest.reason
                continue
            }
            $actionReport = [pscustomobject]@{ model_report = $result; host_actions = @($manifest.applied) }
            $packet = Get-EvidencePacket -Paths $TargetPath -MaxFiles $MaxEvidenceFiles
            $evidenceIds = @($packet.roots.id) + @($packet.sampled_files.id)
            $postActionVerification = $true
            $retryReason = 'Action manifest applied. Verify the refreshed evidence packet only; do not repeat the action.'
            continue
        }

        $validation = Test-StructuredResult -Result $result -EvidenceIds $evidenceIds -CriterionIds $criterionIds
        if ($exitCode -eq 0 -and $validation.valid) {
            $final = [pscustomobject]@{
                success = ([string]$result.status -eq 'completed')
                attempts = $attempt
                model = $Model
                mode = $Mode
                cli_stop_reason = [string]$cliResponse.stop_reason
                result = $result
            }
            break
        }
        $retryReason = if ($validation.valid) { "CLI exit code was $exitCode." } else { $validation.reason }
    }
}
finally {
    $env:ANTHROPIC_API_KEY = $previousApiKey
    $env:ANTHROPIC_BASE_URL = $previousBaseUrl
    if ($null -ne $previousNativeArgumentPassing) {
        $PSNativeCommandArgumentPassing = $previousNativeArgumentPassing
    }
}

if ($null -eq $final) {
    $final = [pscustomobject]@{
        success = $false
        attempts = $attempt
        model = $Model
        mode = $Mode
        error = "The same Grok model did not produce a valid, acceptance-gated result after $attempt attempts."
        last_failure = $retryReason
        last_result = $lastResult
    }
}
$final | ConvertTo-Json -Depth 16
