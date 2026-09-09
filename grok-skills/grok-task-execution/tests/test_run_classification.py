import importlib.util
from pathlib import Path
import unittest
s=importlib.util.spec_from_file_location('classify',Path(__file__).resolve().parents[1]/'scripts/classify-claude-run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class RunClassificationTests(unittest.TestCase):
    def report(self):return {'reviewer':'host','exit_code':0,'protected_inputs_unchanged':True,'required_criteria':['A1'],'criteria':{'A1':'passed'}}
    def final(self,result='done'):return {'type':'result','subtype':'success','is_error':False,'result':result}
    def test_success_needs_actual_acceptance(self):
        r=self.report();r['exit_code']=1
        self.assertEqual(m.classify([self.final()],r)['status'],'failed_acceptance')
    def test_hook_stop_is_not_success(self):
        events=[{'message':{'content':[{'type':'tool_result','is_error':True,'content':'NO_PROGRESS: unchanged'}]}},self.final('')]
        self.assertEqual(m.classify(events,self.report())['status'],'blocked_no_progress')
    def test_missing_criterion_rejected(self):
        r=self.report();r['required_criteria'].append('A2');self.assertFalse(m.classify([self.final()],r)['accepted'])
    def test_verified_recovery_accepted(self):self.assertTrue(m.classify([self.final()],self.report())['accepted'])
if __name__=='__main__':unittest.main()
