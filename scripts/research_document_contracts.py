"""Exercise the installed Trafilatura adapter with synthetic, offline HTML."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.editorial_state import EditorialState
from scripts.research_documents import TOOL_ID
from scripts.skill_router import RouteContext
from scripts.tool_router import run_tool


class ResearchDocumentRuntimeTests(unittest.TestCase):
    def test_local_article_extraction_exact_match_and_cache_for_both_brands(self):
        topics = (("tarih", 18, "Envanterde üç ayrı belge numarası bulunuyor."),
                  ("bakim", 5, "İkinci tabloda örneklemin yaş aralığı açıklanıyor."))
        with tempfile.TemporaryDirectory() as tmp:
            state = EditorialState(Path(tmp) / "doc.sqlite")
            for brand, role, sentence in topics:
                with self.subTest(brand=brand):
                    html = f"""<!doctype html><html lang="tr"><head><title>Deneme yayını</title></head><body>
                        <nav>Gezinti menüsü</nav><article><h1>Editöryal örnek</h1>
                        <p>Bu metin yalnız geliştiricinin çevrimdışı belge okuma deneyi için hazırlanmıştır.
                        {sentence} Başka bir kaynakla karşılaştırma hakkında bir sonuca varılmamıştır.</p>
                        <p>Deney, özgün sayfayı ve alınan metni ayrı saklar. Tarih ve örneklem daha sonra kontrol edilir.
                        Sonuçların ne anlama geldiği insan incelemesine bırakılır.</p></article>
                        <footer>Site alt menüsü</footer>
                        <script src="https://example.org/script.js">Gizli yönlendirme örneği</script>
                        <img src="https://example.org/logo.png" alt="uzak logo"></body></html>"""
                    snapshot = {"html": html, "source_url": "https://example.org/articles/" + brand,
                                "captured_on": "2026-11-27", "analysis_permitted": True,
                                "sha256": hashlib.sha256(html.encode()).hexdigest(), "literal_excerpt": sentence}
                    context = RouteContext(brand, role, "document-evidence")
                    with patch("socket.socket.connect", side_effect=AssertionError("unexpected network")):
                        first = run_tool(context, topic={}, state=state, snapshots={TOOL_ID: snapshot})
                        cached = run_tool(context, topic={}, state=state, snapshots={TOOL_ID: snapshot})
                        unmatched = run_tool(context, topic={}, state=state, snapshots={
                            TOOL_ID: {**snapshot, "literal_excerpt": "Gizli yönlendirme örneği"}})
                    self.assertEqual(first["status"], "success", first["rejected"])
                    result = first["result"]
                    self.assertEqual(result["literal_status"], "literal_found")
                    self.assertEqual(result["snapshot_sha256"], snapshot["sha256"])
                    self.assertIn(sentence, result["evidence_leads"][0]["text"])
                    self.assertNotIn("Gezinti", result["evidence_leads"][0]["text"])
                    self.assertFalse(result["live_http"])
                    self.assertFalse(result["claim_verified"])
                    self.assertTrue(result["content_is_untrusted"])
                    self.assertEqual(result["external_api_calls"], 0)
                    self.assertEqual(cached["status"], "cache")
                    self.assertIsNone(cached["executed_adapter"])
                    self.assertEqual(first["executed_adapter"]["id"], TOOL_ID)
                    self.assertEqual(unmatched["result"]["literal_status"], "literal_not_found")
                    self.assertEqual(unmatched["result"]["evidence_leads"], [])
