import unittest
from unittest.mock import patch

from scripts import skill_registry


class CineCodeNotesTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = skill_registry.registry_view()
        self.notes = {key: entry for key, entry in self.snapshot["entries"].items()
                      if key.startswith("cinecode:")}

    def test_six_distinct_techniques_and_no_duplicate_openmontage_categories(self):
        self.assertEqual(set(self.notes), {f"cinecode:{name}" for name in (
            "preview-depth", "camera-cut-continuity", "motivated-light", "sound-perspective",
            "reference-form", "preflight-frame-sampling",
        )})
        original = {key.split(":")[1] for key in self.snapshot["entries"] if key.startswith("openmontage:")}
        self.assertEqual(len(original), 8)
        self.assertTrue(original.isdisjoint(key.split(":")[1] for key in self.notes))

    def test_notes_have_pinned_mit_provenance_and_no_executable_adapter(self):
        for note in self.notes.values():
            source = note["source"]
            self.assertEqual(source["repository"], "sarpstar/cinecode")
            self.assertRegex(source["revision"], r"^[a-f0-9]{40}$")
            self.assertEqual(source["license_path"], "LICENSE")
            self.assertTrue(source["path"].startswith("references/"))
            base = f"https://github.com/{source['repository']}/blob/{source['revision']}/references/"
            self.assertTrue(all(link.startswith(base) for link in source.get("docs", [])))
            self.assertEqual(note["license"], {"code": "MIT", "scope": "upstream_reference"})
            self.assertEqual(note["kind"], "knowledge")
            self.assertEqual(note["use"]["mode"], "reference")
            self.assertIsNone(note["adapter"])
            self.assertFalse(note["security"]["authorizes_execution"])
            self.assertFalse(note["cost"]["metered_or_paid_allowed"])
            self.assertEqual(note["test"]["status"], "guidance_contract_only")

    def test_routing_reaches_relevant_roles_and_keeps_both_rosters(self):
        experts = self.snapshot["experts"]
        for brand, count in (("tarih", 14), ("bakim", 16)):
            primary = {key for key, item in experts.items() if item["brand"] == brand and item["primary"]}
            mapped = {key for key in primary if self.notes.keys() & set(experts[key]["entry_ids"])}
            self.assertEqual(len(primary), 20)
            self.assertEqual(len(mapped), count)
        for brand, role in (("tarih", 14), ("bakim", 17)):
            notes = skill_registry.registry_view(brand, role)["entries"]
            self.assertIn("cinecode:sound-perspective", notes)
            self.assertNotIn("cinecode:reference-form", notes)
        self.assertIn("cinecode:motivated-light", skill_registry.registry_view("bakim", 13)["entries"])

    def test_knowledge_is_not_offered_as_a_production_tool(self):
        for item in self.snapshot["experts"].values():
            options = skill_registry.review_options(item["brand"], item["id"])
            self.assertTrue(all(not name.startswith("cinecode") for name in options))

    def test_reading_the_registry_needs_no_hooks_execution_or_network(self):
        skill_registry._inventory.cache_clear()
        with (patch("scripts.media_tools.requests.get", side_effect=AssertionError("network")),
              patch("subprocess.Popen", side_effect=AssertionError("execution"))):
            view = skill_registry.registry_view("tarih", 13)
        self.assertIn("cinecode:preview-depth", view["entries"])
        self.assertIn("cinecode:camera-cut-continuity", view["entries"])
