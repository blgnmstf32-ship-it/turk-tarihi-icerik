import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import requests

from scripts.editorial_llm import discussion_completed, review
from scripts.editorial_state import EditorialState


SETTINGS = {"editorial_intelligence": {"free_llm_enabled": True}}
ENV = {"ENABLE_FREE_LLM": "1", "OPENROUTER_API_KEY": "test-secret-key"}
CANDIDATES = [{"id": "antikythera", "sources": [{"url": "https://example.org/paper"}]}]
MODEL = "google/gemma-4-31b-it:free"


def response(status=200, data=None, headers=None):
    reply = Mock(status_code=status, headers=headers or {})
    reply.json.return_value = data
    return reply


def answer(message=None, model=MODEL):
    if message is None:
        message = json.dumps({"rationale": "Kaynak ve izlenme verileri yeterli."})
    return response(data={"model": model, "choices": [{"message": {"content": message}}]})


def quota(remaining):
    return Mock(return_value=response(data={"data": {"free_model_daily_requests": {"remaining": remaining}}}))


class EditorialRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.state = Path(tmp.name) / "state.db"
        env = patch.dict("os.environ", ENV, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.sleep = Mock()

    def run_review(self, calls, reader=None, **kwargs):
        return review(SETTINGS, kwargs.pop("candidates", CANDIDATES), {}, calls,
                      state_path=self.state, quota_reader=reader or quota(50), sleep=self.sleep, **kwargs)

    def test_timeout_429_invalid_json_and_empty_answer_can_retry_then_complete(self):
        limited = response(429, {"error": {"code": 429}}, {"Retry-After": "4"})
        post = Mock(side_effect=[requests.Timeout("test-secret-key"), limited, answer(),
                                 answer("{"), answer(), answer(" "), answer(), answer()])
        result = self.run_review(post)
        self.assertTrue(discussion_completed(result))
        self.assertEqual(result["calls"], 8)
        self.assertEqual([item["status"] for item in result["stages"][0]["attempts"]],
                         ["timeout", "rate_limited", "proposal"])
        self.assertEqual(result["stages"][0]["attempts"][1]["http_status"], 429)
        self.assertEqual(result["stages"][1]["attempts"][0]["status"], "invalid_json")
        self.assertEqual(result["stages"][1]["attempts"][0]["model"], MODEL)
        self.assertEqual(result["stages"][2]["attempts"][0]["status"], "empty_response")
        self.assertTrue(any(call.args[0] >= 4 for call in self.sleep.call_args_list))
        self.assertNotIn("test-secret-key", json.dumps(result))

    def test_http_200_with_upstream_rate_limit_reports_both_codes(self):
        limited = response(200, {"error": {"code": 429}}, {"Retry-After": "2"})
        post = Mock(side_effect=[limited, answer(), answer(), answer(), answer()])
        result = self.run_review(post)
        first = result["stages"][0]["attempts"][0]
        self.assertEqual((first["status"], first["http_status"], first["upstream_error_code"]),
                         ("rate_limited", 200, 429))
        self.assertTrue(discussion_completed(result))

    def test_long_retry_after_stops_with_remaining_roles_unattempted(self):
        post = Mock(side_effect=[answer(), response(429, {"error": {"code": 429}}, {"Retry-After": "3600"})])
        result = self.run_review(post)
        self.assertEqual(result["calls"], 2)
        self.assertFalse(discussion_completed(result))
        self.assertIsNone(result["decision"])
        self.assertEqual([stage["status"] for stage in result["stages"]],
                         ["proposal", "failed", "not_attempted", "not_attempted"])
        self.assertEqual(result["stages"][1]["reason"], "retry_after_exceeds_window")
        self.sleep.assert_not_called()

    def test_failed_role_keeps_previous_reply_and_resumes_with_same_job_evidence(self):
        original = self.run_review(Mock(side_effect=[answer(), response(401)]), run_id="12")
        self.assertFalse(discussion_completed(original))
        self.assertEqual(original["stages"][1]["http_status"], 401)
        replacement = [{"id": "different", "sources": []}]
        post = Mock(side_effect=[answer(), answer(), answer()])
        resumed = self.run_review(post, candidates=replacement, run_id="12")
        self.assertTrue(discussion_completed(resumed))
        self.assertEqual(resumed["calls"], 3)
        self.assertEqual(resumed["cached_roles"], 1)
        self.assertEqual(resumed["stages"][0]["model"], MODEL)
        request = post.call_args_list[0].kwargs["json"]["messages"][1]["content"]
        self.assertEqual(json.loads(request)["candidate_ids"], ["antikythera"])
        full_cache = self.run_review(Mock(side_effect=AssertionError("no POST")),
                                     reader=Mock(side_effect=AssertionError("no GET")), run_id="12")
        self.assertTrue(discussion_completed(full_cache))
        self.assertEqual(full_cache["calls"], 0)
        self.assertEqual(full_cache["cached_roles"], 4)

    def test_server_and_local_daily_budgets_include_failed_requests(self):
        low = quota(1)
        post = Mock(return_value=answer("{"))
        result = self.run_review(post, reader=low)
        self.assertEqual(result["calls"], 1)
        self.assertEqual(result["stages"][0]["reason"], "request_budget_exhausted")
        self.sleep.assert_not_called()
        state = EditorialState(self.state)
        for _ in range(39):
            self.assertIsNotNone(state.reserve(40))
        never = Mock()
        result = self.run_review(never)
        never.assert_not_called()
        self.assertEqual(result["calls"], 0)
        self.assertEqual(result["stages"][0]["reason"], "request_budget_exhausted")

    def test_exhausts_per_role_attempt_limit_and_global_cutoff(self):
        post = Mock(side_effect=[answer("{")] * 3)
        result = self.run_review(post)
        self.assertEqual(result["calls"], 3)
        self.assertFalse(discussion_completed(result))
        post = Mock(side_effect=[answer("{"), answer("{"), answer()] * 2 + [answer("{"), answer("{")])
        result = self.run_review(post)
        self.assertEqual(result["calls"], 8)
        self.assertFalse(discussion_completed(result))
        self.assertEqual(result["stages"][2]["reason"], "request_budget_exhausted")

    def test_successful_model_response_has_credentials_removed(self):
        message = json.dumps({"rationale": "test-secret-key sk-or-v1-example123"})
        post = Mock(return_value=answer(message))
        result = self.run_review(post)
        self.assertTrue(discussion_completed(result))
        self.assertNotIn("test-secret-key", json.dumps(result))
        self.assertNotIn(b"sk-or-v1-example123", self.state.read_bytes())
