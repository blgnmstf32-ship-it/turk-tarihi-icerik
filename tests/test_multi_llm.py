import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

import requests

from scripts import cloudflare_editorial as cloud
from scripts.editorial_state import EditorialState
from scripts.gemini_editorial import GeminiReviewSession
from scripts.multi_llm_smoke import checks_for


ENV = {
    "CLOUDFLARE_API_TOKEN": "cloud-token", "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
    "GEMINI_API_KEY": "gemini-key", "GEMINI_FREE_TIER_CONFIRMED": "1", "ENABLE_GEMINI_EDITORIAL": "1",
    "NVIDIA_API_KEY": "unused-nvidia", "GROQ_API_KEY": "unused-groq",
}
GOOD = {"answer": "Bir kaynak olarak verilen kayıtları incele ve kesin hüküm verme."}


def response(status=200, body=None):
    return mock.Mock(status_code=status, headers={}, json=lambda: body)


def cloud_answer(value=GOOD):
    return response(body={
        "choices": [{"message": {"content": json.dumps(value, ensure_ascii=False)}}],
        "usage": {"prompt_tokens": 150, "completion_tokens": 80},
    })


def validate(raw):
    value = json.loads(raw)
    return (value, None) if set(value) == {"answer"} else (None, "invalid_schema")


class MultiLlmTests(TestCase):
    def setUp(self):
        self.root = TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.state = EditorialState(Path(self.root.name) / "router.sqlite3")
        env = mock.patch.dict("os.environ", ENV, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.billing = mock.Mock(return_value=response(body={"success": True, "result": []}))
        self.pricing = mock.Mock(return_value=response(body={"data": {}}))
        self.delay = mock.Mock()

    def session(self, gemini, cf, *, brand="tarih", key=""):
        return GeminiReviewSession(key, self.state, brand=brand, routed=True, requester=gemini,
                                   cloud_requester=cf, cloud_reader=self.billing, quota_reader=self.pricing,
                                   sleep=self.delay, quota_path=Path(self.root.name) / "budget.sqlite3")

    def test_gemini_quota_routes_to_cloudflare_immediately_then_reuses_result(self):
        google = mock.Mock(return_value=response(429, {"error": {"status": "RESOURCE_EXHAUSTED"}}))
        cf = mock.Mock(return_value=cloud_answer())
        session = self.session(google, cf)
        args = ("Alan Araştırmacısı", "Kısa Türkçe öneri", {"id": "same"}, validate)
        result = session.evaluate(*args)
        self.assertEqual((result["status"], result["model"]), ("proposal", cloud.GEMMA))
        self.assertEqual([a["http_status"] for a in result["attempts"]], [429, 200])
        self.assertEqual(self.session(google, cf).evaluate(*args)["response_source"], "cache")
        self.assertEqual(session.provider_priority, ["gemini_free", "cloudflare_workers_ai"])
        self.assertNotIn("cloud-token", json.dumps(result))
        google.assert_called_once()
        cf.assert_called_once()
        self.assertTrue(cf.call_args.args[0].endswith("/ai/v1/chat/completions"))
        self.assertNotIn("tools", cf.call_args.kwargs["json"])
        self.assertEqual(cf.call_args.kwargs["json"]["max_completion_tokens"], 1600)
        self.assertFalse(cf.call_args.kwargs["allow_redirects"])
        self.delay.assert_not_called()

    def test_503_timeout_and_invalid_json_all_reach_cloudflare_with_bounded_retries(self):
        invalid = response(body={"candidates": [{"content": {"parts": [{"text": "invalid"}]}}]})
        for i, failure in enumerate((response(503), requests.Timeout(), invalid)):
            with self.subTest(i=i):
                cf = mock.Mock(return_value=cloud_answer())
                google = mock.Mock(side_effect=[failure, failure])
                self.state = EditorialState(Path(self.root.name) / f"router-{i}.sqlite3")
                session = self.session(google, cf)
                session.budget.db.execute("DELETE FROM usage")
                reply = session.evaluate("İçerik Stratejisti", "Kısa Türkçe öneri", {"id": i}, validate)
                self.assertEqual((reply["status"], reply["model"]), ("proposal", cloud.GEMMA))
                self.assertEqual(google.call_count, 2)
                cf.assert_called_once()

    def test_cloudflare_returns_to_zero_cost_openrouter_when_language_is_invalid(self):
        def post(url, **kwargs):
            if "googleapis.com" in url:
                return response(429)
            self.assertEqual(kwargs["json"]["provider"]["max_price"], dict(prompt=0, completion=0, request=0))
            return response(body={"model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
                                  "choices": [{"message": {"content": json.dumps(GOOD)}}]})
        cf = mock.Mock(return_value=cloud_answer({"answer": "Always read the available source materials first."}))
        session = self.session(post, cf, key="test-openrouter")
        result = session.evaluate("İçerik Stratejisti", "Kısa Türkçe öneri", {}, validate)
        self.assertEqual(result["provider"], "openrouter_free")
        self.assertEqual(result["attempts"][1]["status"], "turkish_prose_not_confirmed")
        self.assertEqual(session.calls, 1)
        self.assertEqual(session.provider_priority, ["gemini_free", "cloudflare_workers_ai", "openrouter_free"])

    def test_billing_denial_prevents_inference_and_task_resumes_after_recovery(self):
        self.billing.return_value = response(403)
        cf = mock.Mock(return_value=cloud_answer())
        google = mock.Mock(return_value=response(429))
        task = ("Alan Araştırmacısı", "Kısa Türkçe öneri", {"id": "same"}, validate)
        with mock.patch.dict("os.environ", {"ENABLE_GEMINI_EDITORIAL": "0"}):
            failed = self.session(google, cf).evaluate(*task)
            self.assertTrue(failed["queued"])
            cf.assert_not_called()
            with self.state.connect() as db:
                self.assertEqual(db.execute("SELECT id, brand FROM queued_reviews").fetchone(),
                                 (failed["task_id"], "tarih"))
            self.billing.return_value = response(body={"success": True, "result": []})
            result = self.session(google, cf).evaluate(*task)
            self.assertEqual(result["status"], "proposal")
            with self.state.connect() as db:
                self.assertIsNone(db.execute("SELECT id FROM queued_reviews").fetchone())
        google.assert_not_called()
        cf.assert_called_once()

    def test_subscription_precheck_rejects_paid_contracts_and_incomplete_results(self):
        for body in (
            {"success": True, "result": [], "result_info": {"total_count": 1}},
            {"success": True, "result": [{"state": "Paid", "price": 5, "rate_plan": {"id": "workers_paid"}}]},
            {"success": True, "result": [{"price": 0, "rate_plan": {"id": "workers-enterprise"}}]},
            {"success": True, "result": [{"price": 0, "rate_plan": {"id": "free", "is_contract": True}}]},
        ):
            self.assertFalse(cloud._free_subscriptions(body))
        self.assertTrue(cloud._free_subscriptions({"success": True, "result":
            [{"price": 0, "state": "Provisioned", "rate_plan": {"id": "workers-free"}}]}))

    def test_atomic_cloudflare_quota_spans_both_brands_and_counts_unmetered_requests(self):
        def reserve(brand):
            return self.state.reserve_cloudflare(brand, cloud.GEMMA, 4501, 9000)
        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(reserve, ("tarih", "bakim")))
        self.assertEqual(sum(uid is not None for uid in ids), 1)
        usage = self.state.cloudflare_report()
        self.assertEqual((usage[0]["reserved_neurons"], usage[0]["metered_attempts"], usage[0]["usd"]),
                         (4501, 0, 0))

    def test_openrouter_limit_is_still_shared_across_brands(self):
        for _ in range(40):
            self.state.reserve(40)
        request = mock.Mock(return_value=response(429))
        cf = mock.Mock(return_value=response(429))
        for brand in ("tarih", "bakim"):
            result = self.session(request, cf, brand=brand, key="openrouter").evaluate(
                "Alan Araştırmacısı", "Kısa Türkçe öneri", {"brand": brand}, validate)
            self.assertEqual(result["reason"], "request_budget_exhausted")
            self.assertTrue(result["queued"])
        self.assertEqual(request.call_count, 2)
        self.assertEqual(cf.call_count, 4)

    def test_model_specific_probe_never_uses_the_fallback(self):
        google = mock.Mock(return_value=response(503))
        cf = mock.Mock()
        result = self.session(google, cf, key="openrouter").evaluate(
            "Alan Araştırmacısı", "Kısa Türkçe öneri", {}, validate, primary_only=True)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(google.call_count, 2)
        cf.assert_not_called()
        self.pricing.assert_not_called()

    def test_cloudflare_billing_denial_preserves_the_gemini_alternative(self):
        self.billing.return_value = response(403)
        cf = mock.Mock()
        content = json.dumps(GOOD, ensure_ascii=False)
        google = mock.Mock(side_effect=[
            response(503), response(503),
            response(body={"candidates": [{"content": {"parts": [{"text": content}]}}]}),
        ])
        result = self.session(google, cf).evaluate(
            "Alan Araştırmacısı", "Kısa Türkçe öneri", {}, validate)
        self.assertEqual(result["provider"], "gemini")
        self.assertEqual(google.call_count, 3)
        cf.assert_not_called()
        self.billing.assert_called_once()

    def test_benchmark_flags_a_date_missing_from_the_supplied_evidence(self):
        answer = {"hook": "Bu dişli düzenek nereden geliyor?",
                  "text": "Dişliler MÖ 2. yüzyılda yapılmıştır.",
                  "boundary": "Mucidin kim olduğu bilinmiyor.", "fact_ids": [1, 2]}
        checks = checks_for(0, answer)
        self.assertFalse(checks["adds_no_unsupported_numeric_detail"])
        answer["text"] = "Düzeneğin parçalarında dişliler bulunur."
        self.assertTrue(all(checks_for(0, answer).values()))

    def test_glm_probe_read_timeout_does_not_affect_gemma(self):
        cf = mock.Mock(side_effect=[requests.ReadTimeout("secret diagnostics"), cloud_answer()])
        router = self.session(mock.Mock(), cf)
        transport = router.cloudflare
        parse = cloud.turkish_json_parser(validate)
        answer, diagnostic = transport.probe(cloud.GLM, "Kısa Türkçe öneri", {}, parse, 768)
        self.assertIsNone(answer)
        self.assertEqual(diagnostic["status"], "cloudflare_read_timeout")
        self.assertIsNone(diagnostic["http_status"])
        self.assertNotIn("secret diagnostics", json.dumps(diagnostic))
        answer, attempts = transport.evaluate("Kısa Türkçe öneri", {}, parse, 768, 0)
        self.assertEqual(answer, GOOD)
        self.assertEqual([item["model"] for item in attempts], [cloud.GEMMA])
        ledger = {item["model"]: item for item in self.state.cloudflare_report()}
        self.assertEqual(ledger[cloud.GLM]["metered_attempts"], 0)
        self.assertGreater(ledger[cloud.GLM]["reserved_neurons"], 0)
        self.assertEqual(ledger[cloud.GEMMA]["metered_attempts"], 1)

    def test_gemma_model_429_falls_through_once_and_skips_only_that_model(self):
        cf = mock.Mock(side_effect=[response(429), cloud_answer(), cloud_answer()])
        router = self.session(mock.Mock(return_value=response(429)), cf)
        task = ("Alan Araştırmacısı", "Kısa Türkçe öneri", {"id": "a"}, validate)
        result = router.evaluate(*task)
        self.assertEqual(result["model"], cloud.QWEN)
        self.assertEqual([a["http_status"] for a in result["attempts"]], [429, 429, 200])
        next_result = router.evaluate(task[0], task[1], {"id": "b"}, validate)
        self.assertEqual(next_result["model"], cloud.QWEN)
        self.assertEqual(next_result["attempts"][0]["status"], "cloudflare_model_cooldown")
        self.assertEqual([call.kwargs["json"]["model"] for call in cf.call_args_list],
                         [cloud.GEMMA, cloud.QWEN, cloud.QWEN])

    def test_bad_alternate_response_does_not_cool_the_provider(self):
        cf = mock.Mock(side_effect=[cloud_answer({"answer": "English output only for this task."}),
                                    response(503), cloud_answer()])
        router = self.session(mock.Mock(return_value=response(429)), cf)
        result = router.evaluate("İçerik Stratejisti", "Kısa Türkçe öneri", {"id": 1}, validate)
        self.assertTrue(result["queued"])
        next_result = router.evaluate("İçerik Stratejisti", "Kısa Türkçe öneri", {"id": 2}, validate)
        self.assertEqual(next_result["model"], cloud.GEMMA)
        self.assertEqual(next_result["status"], "proposal")

    def test_alternate_respects_shared_reservation_limit(self):
        cf = mock.Mock(return_value=cloud_answer())
        self.assertIsNotNone(self.state.reserve_cloudflare("bakim", cloud.GEMMA, 8999, 9000))
        router = self.session(mock.Mock(return_value=response(429)), cf, brand="tarih")
        result = router.evaluate("Alan Araştırmacısı", "Kısa Türkçe öneri", {}, validate)
        self.assertEqual(result["attempts"][-1]["status"], "cloudflare_daily_limit")
        self.assertTrue(result["queued"])
        cf.assert_not_called()

    def test_live_benchmark_keeps_gemma_success_when_optional_model_fails(self):
        from scripts.multi_llm_smoke import run

        history = {"hook": "Bu dişli düzenek nereden geliyor?", "text": "Parçalarında dişliler vardır.",
                   "boundary": "Mucidin kim olduğu kesin bilinmiyor.", "fact_ids": [1, 2]}
        beauty = {"hook": "Cildin katmanlarını birlikte inceleyelim mi?",
                  "text": "Bu şema cilt katmanlarını gösterir.",
                  "boundary": "Bu temsili şema tedavi sonucu göstermez.", "fact_ids": [1, 2]}
        with mock.patch.object(cloud.requests, "get", self.billing), mock.patch.object(
            cloud.requests, "post", side_effect=[cloud_answer(history), cloud_answer(beauty),
                                                  cloud_answer(beauty), requests.ReadTimeout()],
        ):
            report = run(self.state, Path(self.root.name) / "fixture.sqlite3", "unit")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["simulated_gemini_responses"], [429])
        self.assertEqual(report["real_cloudflare_model_calls"], 4)
        self.assertTrue(all(row["case_passed"] for row in report["cases"]))
        qwen, glm = report["optional_model_checks"]
        self.assertTrue(qwen["case_passed"])
        self.assertFalse(glm["case_passed"])
        self.assertEqual(glm["attempts"][0]["status"], "cloudflare_read_timeout")
