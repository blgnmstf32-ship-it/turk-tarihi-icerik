import os,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
from scripts.run import ROOT, load_json
from scripts.ai_agents import run_agents

class AIAgentTests(unittest.TestCase):
    def test_disabled_without_explicit_opt_in(self):
        with patch.dict(os.environ,{'OPENROUTER_API_KEY':'','ENABLE_20_LLM_AGENTS':'0'}):
            with tempfile.TemporaryDirectory() as d:
                r=run_agents(load_json(ROOT/'data/topics.json')[0],load_json(ROOT/'config/agents.json'),d)
                self.assertEqual(r['calls'],0)
                self.assertFalse(r['enabled'])
    def test_twenty_distinct_model_calls_with_mock(self):
        class FakeResp:
            def raise_for_status(self):pass
            def json(self):return {'choices':[{'message':{'content':'Review suggestion only'}}]}
        history=[]
        def fake_post(url,**kwargs):
            history.append(kwargs['json']['messages'][0]['content']);return FakeResp()
        with patch.dict(os.environ,{'OPENROUTER_API_KEY':'test','ENABLE_20_LLM_AGENTS':'1'}), patch('scripts.ai_agents.time.sleep',lambda x:None):
            with tempfile.TemporaryDirectory() as d:
                r=run_agents(load_json(ROOT/'data/topics.json')[0],load_json(ROOT/'config/agents.json'),d,fake_post,
                    {'editorial_intelligence':{'free_llm_enabled':True}})
                self.assertEqual(r['calls'],20)
                self.assertEqual(r['separate_llm_roles_completed'],20)
                self.assertEqual(len(set(history)),20)
                self.assertFalse(r['verified_historical_sources'])
