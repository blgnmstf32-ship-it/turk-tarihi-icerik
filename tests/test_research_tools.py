import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts.editorial_research import trend_observation
from scripts.editorial_state import EditorialState
from scripts.reels_editorial import specialist_guidance
from scripts.research_documents import TOOL_ID, read_snapshot, ResearchInputError
from scripts.skill_registry import registry_view
from scripts.skill_router import RouteContext, select_knowledge
from scripts.tool_router import run_tool


class ResearchToolsTests(unittest.TestCase):
    def test_registry_preserves_legacy_roles_and_separates_knowledge_from_tool(self):
        snapshot = registry_view()
        entries = snapshot["entries"]
        new = {"last30days:trend-window", "open-research:evidence-scope", "factual-research:claim-passage",
               "research:google-trends-rss", TOOL_ID}
        self.assertGreaterEqual(len(entries.keys() - new), 144)
        self.assertEqual(sum(row["primary"] for row in snapshot["experts"].values()), 40)
        for identifier in new - {TOOL_ID}:
            self.assertEqual(entries[identifier]["kind"], "knowledge")
            self.assertIsNone(entries[identifier]["adapter"])
        self.assertEqual(entries[TOOL_ID]["kind"], "tool")
        self.assertEqual(entries[TOOL_ID]["license"]["code"], "Apache-2.0")

    def test_research_briefs_are_bounded_and_tasks_stay_separate(self):
        trend = select_knowledge(RouteContext("bakim", 7, "trend"))
        self.assertEqual([row["id"] for row in trend], ["research:google-trends-rss", "last30days:trend-window"])
        history = specialist_guidance({"id": 18, "reels_review": {"technique": "rights"}}, "tarih")
        care = specialist_guidance({"id": 4, "reels_review": {"technique": "rights"}}, "bakim")
        for guide in (history, care):
            self.assertEqual(len(guide["skill_notes"]), 2)
            self.assertIn("Karşı kanıtı", guide["skill_notes"][0])
            self.assertIn("Ön baskı", guide["skill_notes"][1])
            self.assertLessEqual(sum(map(len, guide["skill_notes"])), 640)
        self.assertEqual(select_knowledge(RouteContext("bakim", 16, "document-evidence")), [])

    def test_tool_router_rejects_wrong_role_and_knowledge_as_an_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = EditorialState(Path(tmp) / "research.sqlite")
            unauthorized = run_tool(RouteContext("bakim", 16, "document-evidence"), topic={}, state=state)
            note = run_tool(RouteContext("tarih", 18, "document-evidence"), topic={}, state=state,
                            preferred="factual-research:claim-passage")
        self.assertEqual(unauthorized["rejected"][0]["reason"], "role_not_allowed")
        self.assertEqual(note["rejected"][0]["reason"], "knowledge_or_asset_reference")
        self.assertIsNone(unauthorized["executed_adapter"])
        self.assertIsNone(note["executed_adapter"])

    def test_preflight_rejects_invalid_provenance_before_importing_parser(self):
        html = "<html><body><p>Özgün metin.</p></body></html>"
        snapshot = {"html": html, "source_url": "https://example.org/article", "captured_on": "2026-11-25",
                    "sha256": hashlib.sha256(html.encode()).hexdigest(), "analysis_permitted": True}
        with patch("scripts.research_documents.version", side_effect=AssertionError("imported before preflight")):
            for changes, reason in (
                ({"analysis_permitted": False}, "missing_analysis_permission"),
                ({"sha256": "0" * 64}, "snapshot_hash_mismatch"),
                ({"source_url": "file:///tmp/source.html"}, "canonical_https_source_required"),
                ({"source_url": "https://example.org/article?session=private"}, "canonical_https_source_required"),
                ({"captured_on": "2026-02-30"}, "invalid_capture_date"),
                ({"html": "ö" * 60_001}, "invalid_html_snapshot"),
                ({"literal_excerpt": "kısa"}, "invalid_literal_excerpt"),
            ):
                with self.subTest(reason=reason), self.assertRaisesRegex(ResearchInputError, reason):
                    read_snapshot({**snapshot, **changes})

    def test_unreviewed_parser_version_is_reported_as_unavailable(self):
        html = "<p>İncelenecek metin</p>"
        snapshot = {"html": html, "source_url": "https://example.org/article", "captured_on": "2026-11-25",
                    "sha256": hashlib.sha256(html.encode()).hexdigest(), "analysis_permitted": True}
        with tempfile.TemporaryDirectory() as tmp, patch("scripts.research_documents.version", return_value="0"):
            result = run_tool(RouteContext("tarih", 3, "document-evidence"), topic={},
                              state=EditorialState(Path(tmp) / "state"), snapshots={TOOL_ID: snapshot})
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["rejected"][0]["reason"], "unreviewed_parser_version")
        self.assertIsNone(result["result"])

    def test_trend_keeps_source_time_and_bucket_without_inventing_metrics(self):
        rss = ET.fromstring('''<item xmlns:ht="https://trends.google.com/trending/rss">
            <title>Örnek arama</title><link>https://trends.google.com/trending?geo=TR</link>
            <pubDate>Fri, 27 Nov 2026 05:30:00 +0300</pubDate><ht:approx_traffic>2000+</ht:approx_traffic>
            </item>''')
        feed = "https://trends.google.com/trending/rss?geo=TR"
        recorded = trend_observation(rss, feed, "2026-11-27T03:00:00+00:00")
        self.assertEqual((recorded["published_at_utc"], recorded["approx_search_bucket"], recorded["feed"]),
                         ("2026-11-27T02:30:00+00:00", "2000+", feed))
        self.assertEqual(recorded["evidence_type"], "trend_signal_only")
        missing = trend_observation(ET.fromstring("<item><pubDate>bad</pubDate></item>"), feed, "observed")
        self.assertIsNone(missing["published_at_utc"])
        self.assertIsNone(missing["approx_search_bucket"])
        self.assertNotIn("instagram_reach", recorded)
