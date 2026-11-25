import base64
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
from datetime import datetime, timezone, timedelta

from PIL import Image

from scripts import gemini_editorial, gemini_tts, nano_banana
from scripts.editorial_state import EditorialState
from scripts.provider_budget import Budget, image_quote


class DualProviderTests(TestCase):
    def test_shared_pending_cost_reduces_remaining_month_budget(self):
        with TemporaryDirectory() as tmp:
            budget = Budget(Path(tmp) / "quota.db")
            now = datetime(2026, 11, 2, tzinfo=timezone.utc)
            with mock.patch("scripts.provider_budget.MONTHLY_CAP", image_quote("batch", 2)):
                self.assertTrue(budget.reserve_image("first", "tarih", nano_banana.MODEL, "batch", 1, now))
                self.assertTrue(budget.reserve_image("second", "bakim", nano_banana.MODEL, "batch", 1, now))
                self.assertFalse(budget.reserve_image("third", "bakim", nano_banana.MODEL, "batch", 1, now))
                self.assertFalse(budget.reserve_image("third", "bakim", nano_banana.MODEL, "batch", 1, now+timedelta(days=31)))
                self.assertEqual(len(budget.report()), 2)

    def test_free_quota_is_shared_between_brands_by_model_and_pacific_day(self):
        with TemporaryDirectory() as tmp:
            budget = Budget(Path(tmp) / "quota.db")
            now = datetime(2026, 11, 2, 7, 45, tzinfo=timezone.utc)
            self.assertTrue(budget.reserve_free("a", "tarih", "flash", 80, (2, 100, 1), now))
            self.assertFalse(budget.reserve_free("b", "bakim", "flash", 10, (2, 100, 1), now))
            self.assertTrue(budget.reserve_free("b", "bakim", "flash", 10, (2, 100, 1), now+timedelta(minutes=20)))
            self.assertTrue(budget.reserve_free("c", "bakim", "lite", 100, (2, 100, 1), now))

    def test_batch_submits_only_after_sync_and_does_not_repost(self):
        with TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"GEMINI_IMAGE_API_KEY": "only-images",
                                                                      "GEMINI_API_KEY": "free"}):
            db = Budget(Path(tmp) / "quota.db")
            timeline = []
            def request(url, **kwargs):
                timeline.append("request")
                self.assertTrue(url.endswith(":batchGenerateContent"))
                self.assertEqual(kwargs["headers"]["x-goog-api-key"], "only-images")
                req = kwargs["json"]["batch"]["inputConfig"]["requests"]["requests"][0]["request"]
                self.assertEqual(req["generationConfig"]["imageConfig"]["aspectRatio"], "9:16")
                return mock.Mock(status_code=200, json=lambda: {"name": "batches/testid"})

            args = (db, lambda: timeline.append("sync"), "tarih",
                    ["An original 16th-century chartmaker illustration."], Path(tmp) / "output.jpg")
            result = nano_banana.submit(*args, confirmed=True, requester=request)
            self.assertEqual(timeline, ["sync", "request", "sync"])
            self.assertEqual(nano_banana.submit(*args, confirmed=True, requester=request)["cloud_requests"], 0)
            self.assertEqual(result["operation"], "batches/testid")

    def test_a_failed_durable_checkpoint_prevents_paid_call(self):
        with TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"GEMINI_IMAGE_API_KEY": "paid"}):
            db = Budget(Path(tmp) / "quota.db")
            request = mock.Mock()
            sync = mock.Mock(side_effect=RuntimeError("reservation unavailable"))
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                nano_banana.submit(db, sync, "tarih", ["A vertical neutral illustration."],
                                   Path(tmp) / "output.jpg", confirmed=True, requester=request)
            request.assert_not_called()

    def test_tts_cannot_use_paid_project_or_wrong_brand_voice(self):
        with mock.patch.dict(os.environ, {"GEMINI_IMAGE_API_KEY": "same", "GEMINI_API_KEY": "same"}):
            request = mock.Mock()
            with self.assertRaisesRegex(RuntimeError, "görsel"):
                gemini_tts.request_audio("brief", True, request)
            with self.assertRaisesRegex(ValueError, "marka"):
                gemini_tts.request_audio("brief", True, request, brand="tarih", voice="Leda")
            request.assert_not_called()

    def test_free_model_route_caches_valid_result_by_brand(self):
        with TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"GEMINI_API_KEY": "free",
                "GEMINI_FREE_TIER_CONFIRMED": "1", "ENABLE_GEMINI_EDITORIAL": "1"}):
            response = mock.Mock(status_code=200)
            response.json.return_value = {"candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}],
                                          "usageMetadata": {"promptTokenCount": 9, "candidatesTokenCount": 4}}
            requester = mock.Mock(return_value=response)
            session = gemini_editorial.GeminiReviewSession("", EditorialState(Path(tmp)/"cache.db"),
                     requester=requester, quota_path=Path(tmp)/"quota.db", brand="bakim")
            args = ("Genel Yayın Yönetmeni", "Instruction", {}, lambda raw: (json.loads(raw), None))
            self.assertEqual(session.evaluate(*args)["model"], gemini_editorial.FLASH)
            self.assertEqual(session.evaluate(*args)["response_source"], "cache")
            self.assertEqual(session.gemini_attempts, 1)
            self.assertEqual(session.budget.report()[0]["input_tokens"], 9)
            requester.assert_called_once()

    def test_completed_documented_rest_batch_shape_is_decoded(self):
        with TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"GEMINI_IMAGE_API_KEY": "paid"}):
            target = Path(tmp)
            budget = Budget(target / "quota.db")
            budget.reserve_image("one", "tarih", nano_banana.MODEL, "batch", 1)
            budget.finish("one", "submitted", operation="batches/example")
            encoded = io.BytesIO()
            Image.new("RGB", (768, 1376), (212, 120, 85)).save(encoded, "PNG")
            part = {"inlineData": {"mimeType": "image/png",
                                  "data": base64.b64encode(encoded.getvalue()).decode()}}
            result = {"candidates": [{"content": {"parts": [part]}}]}
            row = {"metadata": {"key": "0"}, "response": result}
            response = mock.Mock(status_code=200)
            response.json.return_value = {"state": "JOB_STATE_SUCCEEDED", "dest": {"inlinedResponses": [row]}}
            stats = nano_banana.collect_batch(budget, mock.Mock(), "one", target, confirmed=True,
                                               requester=mock.Mock(return_value=response))
            self.assertEqual(stats["state"], "complete")
            with Image.open(target / "image-00.jpg") as image:
                self.assertEqual(image.size, (1080, 1920))

    def test_503_tries_same_model_on_interactions_then_alternative_in_order(self):
        with TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"GEMINI_API_KEY": "free",
                 "GEMINI_FREE_TIER_CONFIRMED": "1", "ENABLE_GEMINI_EDITORIAL": "1"}):
            failed = mock.Mock(status_code=503, headers={}, json=lambda: {"error": {"status": "UNAVAILABLE"}})
            success = mock.Mock(status_code=200,
                json=lambda: {"candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}]})
            request = mock.Mock(side_effect=[failed, failed, success])
            sleep = mock.Mock()
            review = gemini_editorial.GeminiReviewSession("", EditorialState(Path(tmp) / "cache"),
                  requester=request, quota_path=Path(tmp) / "budget", sleep=sleep)
            result = review.evaluate("Genel Yayın Yönetmeni", "Instruction", {}, lambda raw: (json.loads(raw), None))
            self.assertEqual(result["model"], gemini_editorial.LITE)
            self.assertEqual([step["api"] for step in result["attempts"]],
                             ["generateContent", "interactions", "generateContent"])
            self.assertEqual([step["provider_status"] for step in result["attempts"][:2]],
                             ["UNAVAILABLE", "UNAVAILABLE"])
            self.assertEqual([args.args[0] for args in sleep.call_args_list], [2, 4])

    def test_31_day_schedule_leaves_a_margin_under_18_dollars(self):
        from datetime import date
        from scripts.provider_budget import batch_plan, MONTHLY_CAP

        first = date(2026, 12, 1)
        plan = batch_plan(first, MONTHLY_CAP)
        total = sum(row["image_count"] for row in plan)
        self.assertEqual(len(plan), 31)
        self.assertLess(total, 35*31)
        self.assertLessEqual(image_quote("batch", total), MONTHLY_CAP)
        self.assertLessEqual(max(row["image_count"] for row in plan) - min(row["image_count"] for row in plan), 1)

    def test_metered_image_cost_uses_distinct_pricing_for_image_and_text_tokens(self):
        info = {"input_tokens": 76, "output_tokens": 1557, "image_tokens": 1120, "thinking_tokens": 0}
        self.assertEqual(nano_banana.measured_image_cost("batch", info), 17138)
