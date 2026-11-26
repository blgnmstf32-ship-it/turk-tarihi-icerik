from copy import deepcopy
from urllib.parse import urlsplit
import unittest
from unittest.mock import patch

from scripts import skill_registry


class GeminiSkillNotesTests(unittest.TestCase):
    def setUp(self):
        snapshot = skill_registry.registry_view()
        self.experts = snapshot["experts"]
        self.entries = {key: row for key, row in snapshot["entries"].items() if key.startswith("gemini:")}

    def test_eight_reviewed_topics_cover_all_numbered_specialists(self):
        names = ("api", "model-selection", "structured-json", "context", "cache",
                 "multimodal", "tts", "image-generation")
        self.assertEqual(set(self.entries), {f"gemini:{name}" for name in names})
        mapped = set().union(*(row["expert_ids"] for row in self.entries.values()))
        self.assertEqual(mapped, {key for key, expert in self.experts.items() if expert["primary"]})
        for expert_id in mapped:
            linked = set(self.experts[expert_id]["entry_ids"]) & self.entries.keys()
            self.assertEqual(linked, {key for key, row in self.entries.items() if expert_id in row["expert_ids"]})

    def test_license_review_and_official_documentation_are_recorded(self):
        for entry in self.entries.values():
            source = entry["source"]
            self.assertEqual(source["repository"], "google-gemini/gemini-skills")
            self.assertRegex(source["revision"], r"^[a-f0-9]{40}$")
            self.assertEqual(source["path"], "skills/gemini-api-dev/SKILL.md")
            self.assertEqual(source["license_path"], "LICENSE")
            self.assertEqual(entry["license"], {"code": "Apache-2.0", "scope": "upstream_reference"})
            self.assertTrue(source["docs"])
            for doc in source["docs"]:
                uri = urlsplit(doc)
                self.assertEqual((uri.scheme, uri.netloc), ("https", "ai.google.dev"))
                self.assertTrue(uri.path.startswith("/gemini-api/docs/"))

    def test_new_notes_never_offer_tools_or_claim_runtime_success(self):
        for entry in self.entries.values():
            self.assertEqual(entry["kind"], "knowledge")
            self.assertEqual(entry["use"]["mode"], "reference")
            self.assertIsNone(entry["adapter"])
            self.assertFalse(entry["security"]["authorizes_execution"])
            self.assertFalse(entry["cost"]["metered_or_paid_allowed"])
            self.assertEqual(entry["test"]["status"], "guidance_contract_only")
        for expert in self.experts.values():
            options = skill_registry.review_options(expert["brand"], expert["id"])
            self.assertFalse(any(name.startswith("gemini") for name in options))

    def test_role_views_select_relevant_notes_and_keep_brands_separate(self):
        for brand, role_id, another_brand in [("tarih", 8, "bakim"), ("bakim", 16, "tarih")]:
            snapshot = skill_registry.registry_view(brand, role_id)
            self.assertEqual(list(snapshot["experts"]), [f"{brand}:{role_id}"])
            self.assertIn("gemini:cache", snapshot["entries"])
            self.assertIn("gemini:tts", snapshot["entries"])
            self.assertNotIn("gemini:image-generation", snapshot["entries"])
            self.assertNotIn(f"{another_brand}:{role_id}", snapshot["experts"])

    def rebuilt_registry(self, edit):
        read = skill_registry._read
        manifest = deepcopy(read("config/skill_registry.json"))
        edit(manifest["gemini_knowledge"])
        with patch.object(skill_registry, "_read",
                          side_effect=lambda path: manifest if path == "config/skill_registry.json" else read(path)):
            skill_registry._inventory.cache_clear()
            try:
                return skill_registry.registry_view()
            finally:
                skill_registry._inventory.cache_clear()

    def test_mutable_source_revisions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "full Git revision"):
            self.rebuilt_registry(lambda source: source.update(revision="main"))

    def test_adding_execution_fields_cannot_enable_a_knowledge_record(self):
        def edit(source):
            source["notes"]["api"].update(mode="local", adapter="scripts/create_reel.py:render_reel",
                                          test="historical_pass")
        entry = self.rebuilt_registry(edit)["entries"]["gemini:api"]
        self.assertIsNone(entry["adapter"])
        self.assertEqual(entry["kind"], "knowledge")
        self.assertEqual(entry["test"]["status"], "guidance_contract_only")
