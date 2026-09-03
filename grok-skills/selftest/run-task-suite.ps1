# Acceptance harness for run-grok-software-task.ps1 (HANDOFF 1.5, criteria 1/3/4).
# stdout of the runner goes to a file untouched, so "pure JSON" is testable.
param(
    [int]$Runs = 1,
    [string]$Label = 'smoke',
    [decimal]$Budget = 0.75,
    [int]$MaxRetries = 3,
    [string]$Model = 'claude-sonnet-4-6',
    [switch]$SkipModelPreflight
)
$ErrorActionPreference = 'Continue'
$script = 'C:\Users\chenha\.claude\skills\grok-software-execution\scripts\run-grok-software-task.ps1'
$logDir = 'D:\tmp\grok-selftest\logs'
if (-not (Test-Path $logDir)) { [void](New-Item -ItemType Directory -Path $logDir -Force) }

for ($i = 1; $i -le $Runs; $i++) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $out = Join-Path $logDir "task-$Label-$i-$stamp.out.json"
    $err = Join-Path $logDir "task-$Label-$i-$stamp.err.txt"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    $extra = @{}
    if ($SkipModelPreflight) { $extra['SkipModelPreflight'] = $true }

    & $script `
        -Task '阅读 fixture 目录，确认重试上限配置值，以及被弃用的端点及其截止日期。只读，不要修改任何文件。' `
        -TargetPath 'D:\tmp\grok-selftest\fixture' `
        -AcceptanceCriteria '指出 config.json 中的 retry_limit 具体数值', '指出 notes.md 中被弃用的端点名称与截止日期' `
        -Mode ReadOnly -MaxRetries $MaxRetries -MaxBudgetUsd $Budget -Model $Model @extra `
        1> $out 2> $err
    $sw.Stop()

    $txt = Get-Content -LiteralPath $out -Raw
    # An empty file must not read as "parsed": $null | ConvertFrom-Json does not throw.
    $parses = $false; $doc = $null
    if (-not [string]::IsNullOrWhiteSpace($txt)) {
        try { $doc = $txt | ConvertFrom-Json -ErrorAction Stop; $parses = $true } catch { $parses = $false }
    }

    "=== RUN $i/$Runs  ($([Math]::Round($sw.Elapsed.TotalSeconds,1))s) ==="
    "stdout_bytes = $((Get-Item $out).Length)   JsonParses = $parses"
    if ($parses) {
        "success      = $($doc.success)   status = $($doc.status)   class = $($doc.class)   attempts = $($doc.attempts)"
        "run_dir      = $($doc.run_dir)"
        if ($doc.PSObject.Properties['error']) { "error        = $($doc.error)" }
        if ($doc.PSObject.Properties['result'] -and $doc.result) {
            "evidence     = $(@($doc.result.verified_evidence).Count) claims"
            foreach ($a in @($doc.result.acceptance_results)) {
                "  $($a.criterion_id) = $($a.verdict)  ev=$($a.evidence_ids -join ',')  $($a.detail)"
            }
            "next_action  = $($doc.result.next_action)"
        }
        $rd = $doc.run_dir
        if ($rd -and (Test-Path $rd)) {
            "run_dir_files= $((Get-ChildItem -LiteralPath $rd | Select-Object -ExpandProperty Name) -join ', ')"
        }
    } else {
        "--- stdout head ---"; ($txt -split "`n" | Select-Object -First 12) -join "`n"
    }
    "stderr_tail  = $((Get-Content -LiteralPath $err -Tail 4) -join ' | ')"
    "logs: $out"
    ""
}
