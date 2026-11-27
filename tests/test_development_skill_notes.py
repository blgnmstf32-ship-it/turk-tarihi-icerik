from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.editorial_state import EditorialState
from scripts.reels_editorial import specialist_guidance
from scripts.skill_registry import registry_view
from scripts.skill_router import RouteContext, select_knowledge
from scripts.tool_router import run_tool


class DevelopmentSkillNotesTests(unittest.TestCase):
    routes = {
        "failure-diagnosis": ("superpowers:isolate-failure", "tarih", 13),
        "task-handoff": ("matt-pocock:handoff-readiness", "bakim", 1),
        "acceptance-review": ("addy-osmani:acceptance-proof", "tarih", 11),
        "local-preview-review": ("anthropic:mobile-preview-check", "bakim", 18),
        "ci-review": ("openai:ci-evidence", "tarih", 19),
    }

    def test_existing_rosters_and_read_only_development_entries(self):
        inventory = registry_view()
        entries = inventory["entries"]
        new = {identifier for identifier, _, _ in self.routes.values()}
        self.assertGreaterEqual(len(entries.keys() - new), 149)
        self.assertEqual(sum(role["primary"] for role in inventory["experts"].values()), 40)
        for identifier in new:
            with self.subTest(entry=identifier):
                row = entries[identifier]
                self.assertEqual(row["kind"], "knowledge")
                self.assertIsNone(row["adapter"])
                self.assertFalse(row["security"]["authorizes_execution"])
                self.assertRegex(row["source"]["revision"], r"^[0-9a-f]{40}$")
        for identifier in ("anthropic:mobile-preview-check", "openai:ci-evidence"):
            self.assertEqual(entries[identifier]["license"]["code"], "Apache-2.0")
            self.assertTrue(entries[identifier]["source"]["license_path"].endswith("/LICENSE.txt"))

    def test_explicit_task_selects_only_the_role_mapped_note(self):
        for task, (identifier, brand, role) in self.routes.items():
            with self.subTest(task=task):
                selected = select_knowledge(RouteContext(brand, role, task))
                self.assertEqual([row["id"] for row in selected], [identifier])
                self.assertEqual(select_knowledge(RouteContext(brand, 8, task)), [])
                self.assertLessEqual(len(selected[0]["guidance"]), 640)

    def test_existing_video_brief_and_tool_routing_do_not_execute_development_notes(self):
        guide = specialist_guidance({"id": 16, "reels_review": {"technique": "edit"}}, "tarih")
        all_dev = {row["guidance"] for task, (_identifier, brand, role) in self.routes.items()
                   for row in select_knowledge(RouteContext(brand, role, task))}
        self.assertTrue(all_dev.isdisjoint(guide.get("skill_notes", [])))
        with TemporaryDirectory() as folder:
            state = EditorialState(Path(folder) / "router.db")
            result = run_tool(RouteContext("tarih", 19, "ci-review"), topic={}, state=state,
                              preferred="openai:ci-evidence")
        self.assertEqual(result["rejected"], [{"id": "openai:ci-evidence", "reason": "knowledge_or_asset_reference"}])
        self.assertIsNone(result["executed_adapter"])
