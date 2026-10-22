"""Offline transport adapter tests. Mock only the network/process boundary."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
PWSH = shutil.which('pwsh')

@unittest.skipUnless(PWSH, 'PowerShell 7 required for adapter tests')
class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.adapter = self.root / 'grok-task-execution/scripts/invoke-grok-step.ps1'
        self.adapter.parent.mkdir(parents=True)
        shutil.copy2(SKILL / 'scripts/invoke-grok-step.ps1', self.adapter)
        common = self.root / 'grok-software-execution/scripts/grok-common.ps1'
        common.parent.mkdir(parents=True)
        original = str(SKILL.parent / 'grok-software-execution/scripts/grok-common.ps1').replace("'", "''")
        mockfile = str(self.root / 'run.json').replace("'", "''")
        callsfile = str(self.root / 'calls.txt').replace("'", "''")
        common.write_text(". '" + original + "'\n" + '''
function Resolve-GrokEndpoint { return [pscustomobject]@{BaseUrl='https://example.invalid/v1';Token='mock';Exe='unused'} }
function Invoke-GrokCli($Endpoint,[string[]]$Arguments,[string]$WorkingDirectory,[int]$TimeoutMs) {
    Add-Content -LiteralPath 'CALLSFILE' -Value 'called'
    $i=[Array]::IndexOf($Arguments,'--tools')
    if($i -lt 0 -or $Arguments[$i+1] -ne ''){throw 'TOOLS MUST BE DISABLED'}
    if($Arguments -notcontains '--strict-mcp-config'){throw 'MCP isolation missing'}
    if($Arguments[[Array]::IndexOf($Arguments,'--model')+1] -ne 'fixture-grok'){throw 'Model substituted'}
    return Get-Content -LiteralPath 'MOCKFILE' -Raw -Encoding utf8 | ConvertFrom-Json
}
'''.replace('MOCKFILE', mockfile).replace('CALLSFILE', callsfile), encoding='utf-8-sig')
        self.request = self.root / 'request.json'
        self.request.write_text(json.dumps(dict(task_id='one', phase='work', goal='synthetic arithmetic', criteria={'A1':'sum'}, evidence=[{'id':'E1','text':'2+3'}], feedback='')), encoding='utf-8')
        self.payload = dict(task_id='one',phase='work',status='ready',deliverable={'sum':5},claims=[],acceptance_results=[],remaining_work=[],next_action='host verify')

    def call(self, origin='https://example.invalid', timeout=False, payload=None, envelope=None, exit_code=0):
        if envelope is None:
            envelope = dict(result=json.dumps(self.payload if payload is None else payload),is_error=False)
        (self.root / 'run.json').write_text(json.dumps(dict(stdout=json.dumps(envelope),stderr='',timedOut=timeout,exitCode=exit_code)),encoding='utf-8')
        cp = subprocess.run([PWSH,'-NoProfile','-File',str(self.adapter),'-RequestFile',str(self.request),'-OutputDirectory',str(self.root / 'call'),'-Model','fixture-grok','-ExpectedOrigin',origin],capture_output=True,text=True,encoding='utf-8',timeout=25)
        return cp

    def test_success_is_not_host_acceptance(self):
        cp=self.call()
        self.assertEqual(cp.returncode,0,cp.stderr)
        result=json.loads(cp.stdout)
        self.assertTrue(result['contract_valid'])
        self.assertFalse(result['tools_enabled'])
        self.assertEqual(result['host_acceptance'],'pending')
        self.assertEqual(result['payload']['deliverable']['sum'],5)

    def test_destination_change_stops_before_call(self):
        cp=self.call(origin='https://elsewhere.invalid')
        self.assertNotEqual(cp.returncode,0)
        self.assertFalse((self.root / 'call').exists())
        self.assertFalse((self.root / 'calls.txt').exists())

    def test_wrong_task_response_rejected(self):
        cp=self.call(payload=dict(self.payload,task_id='other'))
        self.assertEqual(cp.returncode,2,cp.stderr)
        self.assertFalse(json.loads(cp.stdout)['contract_valid'])

    def test_timeout_not_completion(self):
        cp=self.call(timeout=True)
        self.assertEqual(cp.returncode,2,cp.stderr)
        self.assertTrue(json.loads(cp.stdout)['timed_out'])

    def test_outputs_never_overwritten(self):
        cp=self.call()
        self.assertEqual(cp.returncode,0,cp.stderr)
        before=(self.root/'call/result.json').read_bytes()
        cp=self.call()
        self.assertNotEqual(cp.returncode,0)
        self.assertEqual(before,(self.root/'call/result.json').read_bytes())

    def check_failure(self, envelope, expected_class, reason, action):
        cp = self.call(envelope=envelope, exit_code=1)
        self.assertEqual(cp.returncode, 2, cp.stderr)
        result = json.loads(cp.stdout)
        self.assertEqual(result['transport_class'], expected_class)
        self.assertEqual(result['transport_reason'], reason)
        self.assertEqual(result['retry_action'], action)
        self.assertFalse(result['contract_valid'])
        self.assertEqual(result['host_acceptance'], 'pending')
        self.assertEqual((self.root/'calls.txt').read_text().splitlines(), ['called'])
        return result

    def test_model_not_found_503_stops(self):
        self.check_failure(dict(is_error=True, api_error_status=503,
                                result='model_not_found: no available channel'),
                           'hard', 'provider_error', 'stop')

    def test_error_array_model_not_found_stops(self):
        self.check_failure(dict(is_error=True, api_error_status=503, result='',
                                errors=[{'type': 'model_not_found'}]),
                           'hard', 'provider_error', 'stop')

    def test_budget_exhaustion_stops(self):
        self.check_failure(dict(is_error=True, subtype='error_max_budget_usd'),
                           'hard', 'budget_exhausted', 'stop')

    def test_budget_terminal_reason_stops(self):
        self.check_failure(dict(is_error=True, terminal_reason='budget_exhausted'),
                           'hard', 'budget_exhausted', 'stop')

    def test_insufficient_quota_stops(self):
        self.check_failure(dict(is_error=True, api_error_status=429,
                                result='insufficient_quota'),
                           'hard', 'provider_error', 'stop')

    def test_overload_is_not_model_absence_and_never_auto_retries(self):
        self.check_failure(dict(is_error=True, api_error_status=503,
                                result='temporarily overloaded'),
                           'transient', 'provider_error', 'host_review_required')

    def test_failure_receipt_does_not_include_raw_provider_message(self):
        result = self.check_failure(dict(is_error=True, api_error_status=401,
                                         result='invalid_api_key PRIVATE_FIXTURE_VALUE'),
                                    'hard', 'provider_error', 'stop')
        self.assertNotIn('PRIVATE_FIXTURE_VALUE', json.dumps(result))

if __name__=='__main__':
    unittest.main()
