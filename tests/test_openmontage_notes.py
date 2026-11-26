from copy import deepcopy
import unittest
from unittest.mock import patch

from scripts import skill_registry


class OpenMontageNotesTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = skill_registry.registry_view()
        self.notes = {key: entry for key, entry in self.snapshot["entries"].items()
                      if key.startswith("openmontage:")}

    def test_all_eight_research_areas_cover_the_forty_primary_experts(self):
        areas = ("production-handoffs", "specialist-coordination", "scene-tool-fit", "storyboard",
                 "render-provenance", "media-synchronization", "selective-recovery", "cache-revalidation")
        self.assertEqual(set(self.notes), {f"openmontage:{area}" for area in areas})
        matched = {expert_id for item in self.notes.values() for expert_id in item["expert_ids"]}
        primary = {key for key, value in self.snapshot["experts"].items() if value["primary"]}
        self.assertEqual(len(primary), 40)
        self.assertEqual(matched, primary)
        for expert_id in primary:
            entries = self.snapshot["experts"][expert_id]["entry_ids"]
            self.assertEqual(set(entries) & self.notes.keys(),
                             {key for key, item in self.notes.items() if expert_id in item["expert_ids"]})

    def test_license_scope_and_pinned_sources_are_visible(self):
        for entry in self.notes.values():
            origin = entry["source"]
            self.assertEqual(origin["repository"], "OpenMontageInc/OpenMontage")
            self.assertRegex(origin["revision"], r"^[0-9a-f]{40}$")
            self.assertEqual(origin["license_path"], "LICENSE")
            self.assertRegex(origin["path"], r"^(docs|lib|tools|skills|pipeline_defs)/")
            self.assertEqual(entry["license"], {"code": "AGPL-3.0", "scope": "upstream_reference"})

    def test_review_notes_do_not_enter_execution_or_claim_a_render(self):
        for entry in self.notes.values():
            self.assertEqual(entry["kind"], "knowledge")
            self.assertEqual(entry["use"]["mode"], "reference")
            self.assertIsNone(entry["adapter"])
            self.assertFalse(entry["security"]["authorizes_execution"])
            self.assertFalse(entry["cost"]["metered_or_paid_allowed"])
            self.assertEqual(entry["test"], {"status": "guidance_contract_only",
                                             "evidence": "tests/test_openmontage_notes.py"})
        for item in self.snapshot["experts"].values():
            options = skill_registry.review_options(item["brand"], item["id"])
            self.assertTrue(self.notes.keys().isdisjoint(options))
            self.assertNotIn("openmontage", options)

    def test_brand_views_show_relevant_narration_and_specialties(self):
        for brand, role_id, voice in (("tarih", 8, "Charon"), ("bakim", 16, "Sulafat")):
            view = skill_registry.registry_view(brand, role_id)
            self.assertEqual(list(view["experts"]), [f"{brand}:{role_id}"])
            self.assertIn(voice, view["entries"]["openmontage:media-synchronization"]["task"])
            self.assertIn("openmontage:cache-revalidation", view["entries"])
            self.assertNotIn("openmontage:storyboard", view["entries"])

    def test_mutable_source_reference_is_rejected(self):
        source = deepcopy(skill_registry._read("config/skill_registry.json")["openmontage_knowledge"])
        source["revision"] = "main"
        with self.assertRaisesRegex(ValueError, "full Git revision"):
            list(skill_registry._review_notes("openmontage", source, "tests/test_openmontage_notes.py"))

    def test_review_does_not_fetch_or_import_an_upstream_reference(self):
        skill_registry._inventory.cache_clear()
        with (patch("scripts.media_tools.requests.get", side_effect=AssertionError("network")),
              patch("subprocess.Popen", side_effect=AssertionError("command"))):
            self.assertIn("openmontage:selective-recovery", skill_registry.registry_view()["entries"])
