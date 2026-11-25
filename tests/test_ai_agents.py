import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.ai_agents import run_agents
from scripts.editorial_llm import FREE_ATTEMPT_MODELS, review
from scripts.editorial_state import EditorialState
from scripts.run import ROOT, load_json


def response(answer, status=200):
    reply = Mock(status_code=status, headers={})
    reply.json.return_value = {"model": FREE_ATTEMPT_MODELS[0],
                               "choices": [{"message": {"content": json.dumps(answer)}}]}
    return reply


class AIAgentTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.out = Path(temp.name)
        self.state = self.out / "ledger.db"
        self.topic = load_json(ROOT / "data/topics.json")[0]
        self.agents = load_json(ROOT / "config/agents.json")
        self.settings = {"editorial_intelligence": {"free_llm_enabled": True}}
        self.env = {"OPENROUTER_API_KEY": "test-secret", "ENABLE_20_LLM_AGENTS": "1", "ENABLE_FREE_LLM": "1"}
        self.quota = Mock(return_value=Mock(status_code=200))
        self.quota.return_value.json.return_value = {"data": {"free_model_daily_requests": {"remaining": 40}}}

    def run_experts(self, request, prior_calls=4):
        with patch.dict("os.environ", self.env, clear=True):
            return run_agents(self.topic, self.agents, self.out, request, self.settings,
                              editorial={"coordinator_llm": {"calls": prior_calls}},
                              state_path=self.state, quota_reader=self.quota, sleep=Mock())

    def test_disabled_without_explicit_opt_in(self):
        self.env.pop("ENABLE_20_LLM_AGENTS")
        request = Mock()
        result = self.run_experts(request)
        self.assertFalse(result["enabled"])
        self.assertEqual(len(result["roles"]), 20)
        self.assertTrue(all(row["status"] == "not_run" for row in result["roles"]))
        request.assert_not_called()

    def test_every_original_role_can_be_selected_including_role_twenty(self):
        for role_id in range(1, 21):
            with self.subTest(role=role_id):
                request = Mock(side_effect=[
                    response({"rationale":"Konuya özel", "assignments":[{"role_id":role_id,"brief":"Taslak"}]}),
                    response({"suggestion":"Görüş test-secret", "caveat":"İncele", "source_numbers":[1]}),
                    response({"rationale":"Kaynağa göre", "tradeoff":"Elle kontrol", "considered_role_ids":[role_id],
                              "preferred_role_id":role_id}),
                ])
                # Isolate the cache across subtests to simulate each available job.
                self.state = self.out / f"ledger-{role_id}.db"
                result = self.run_experts(request)
                self.assertEqual(result["calls"], 3)
                self.assertEqual(result["separate_llm_roles_completed"], 1)
                self.assertEqual(result["roles"][role_id - 1]["status"], "proposal")
                self.assertEqual(result["comparison"]["answer"]["preferred_role_id"], role_id)
                self.assertNotIn("test-secret", json.dumps(result))
                for call in request.call_args_list:
                    self.assertEqual(call.kwargs["json"]["provider"]["max_price"],
                                     {"prompt":0,"completion":0,"request":0})

    def test_failed_expert_keeps_successful_peer_and_resumes_from_cache(self):
        assignment = response({"rationale":"Görsel ve ses", "assignments":[
            {"role_id":11,"brief":"Görseller"}, {"role_id":14,"brief":"Ses"}]})
        expert = response({"suggestion":"Öneri", "caveat":"İncele", "source_numbers":[1]})
        result = self.run_experts(Mock(side_effect=[assignment, expert, response({}, 401)]))
        self.assertEqual([result["roles"][i]["status"] for i in (10, 13)], ["proposal", "failed"])
        comparison = response({"rationale":"Birlikte değerlendir", "tradeoff":"El ile kontrol",
                               "considered_role_ids":[14,11],"preferred_role_id":11})
        resumed = self.run_experts(Mock(side_effect=[expert, comparison]))
        self.assertEqual((resumed["calls"], resumed["cached_reviews"]), (2, 2))
        self.assertEqual(resumed["separate_llm_roles_completed"], 2)

    def test_editorial_and_specialists_share_daily_ledger_and_runtime_budget(self):
        state = EditorialState(self.state)
        for _ in range(36):
            state.reserve(40)
        with patch.dict("os.environ", self.env, clear=True):
            editorial = review(self.settings, [{"id":"a"}], {}, Mock(return_value=response({"rationale":"Taslak"})),
                               state_path=self.state, quota_reader=self.quota)
        self.assertEqual(editorial["calls"], 4)
        request = Mock()
        result = self.run_experts(request)
        self.assertEqual(result["calls"], 0)
        self.assertEqual(result["dispatch"]["reason"], "request_budget_exhausted")
        result = self.run_experts(request, prior_calls=8)
        self.assertEqual(result["dispatch"]["reason"], "request_budget_exhausted")
        request.assert_not_called()

    def test_editor_cannot_dispatch_specialist_21(self):
        request = Mock(return_value=response({"rationale":"Görsel", "assignments":[{"role_id":21,"brief":"3D"}]}))
        result = self.run_experts(request)
        self.assertEqual(result["calls"], 3)
        self.assertEqual(result["dispatch"]["error_type"], "invalid_schema")
        self.assertTrue(all(row["status"] == "not_run" for row in result["roles"]))
