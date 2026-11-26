from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import media_tools, motion_toolkit, skill_registry
from scripts.reels_editorial import playbook, specialist_guidance


class SkillRegistryTests(unittest.TestCase):
    def test_primary_roles_are_complete_and_both_brands_are_distinct(self):
        snapshot = skill_registry.registry_view()
        for brand, path in skill_registry.ROSTERS.items():
            roster = json.loads((skill_registry.ROOT / path).read_text(encoding="utf-8"))
            selected = {k: x for k, x in snapshot["experts"].items() if x["brand"] == brand}
            self.assertEqual(len(selected), len(roster))
            self.assertEqual(sum(r["primary"] for r in selected.values()), 20)
            for role in roster:
                item = selected[f"{brand}:{role['id']}"]
                self.assertEqual(item["name"], role["name"])
                if item["primary"]:
                    focus = role["reels_review"]["technique"]
                    self.assertIn(f"editorial:{focus}", item["entry_ids"])
                    self.assertEqual(specialist_guidance(role, brand)["method"], playbook()["techniques"][focus])
        history = snapshot["experts"]["tarih:1"]["entry_ids"]
        beauty = snapshot["experts"]["bakim:1"]["entry_ids"]
        self.assertIn("editorial:topic", history)
        self.assertIn("editorial:story", beauty)
        self.assertNotIn("local:turk-history-documentary", beauty)

    def test_all_pinned_motion_skills_keep_revision_paths_and_decisions(self):
        entries = skill_registry.registry_view()["entries"]
        source_rows = {(x["source"]["repository"], x["source"]["revision"], x["source"]["path"]): x
                       for x in entries.values() if "decision" in x["source"]}
        self.assertEqual(len(source_rows), 65)
        for pack in motion_toolkit.skill_index():
            for expected in pack["skills"]:
                row = source_rows[(pack["repository"], pack["commit"], expected["path"])]
                self.assertEqual(row["source"]["decision"], expected["decision"])
                self.assertEqual(row["kind"], "knowledge")
                self.assertIsNone(row["adapter"])
                self.assertEqual(bool(row["expert_ids"]), expected["decision"] == "adapt")
        self.assertEqual(sum(bool(row["expert_ids"]) for row in source_rows.values()), 40)

    def test_review_allowlist_matches_legacy_routes_for_every_role(self):
        for brand in skill_registry.ROSTERS:
            for role_id in range(1, 25):
                legacy = {**media_tools.options(brand, role_id),
                          **{name: tool["use"] for name, tool in motion_toolkit.role_guidance(brand, role_id)["tools"].items()
                             if tool["status"] == "optional"}}
                self.assertEqual(skill_registry.review_options(brand, role_id), legacy, (brand, role_id))
        self.assertNotIn("freesound", skill_registry.review_options("bakim", 17))
        self.assertNotIn("rembg", skill_registry.review_options("tarih", 13))

    def test_source_and_local_adapter_report_separate_evidence(self):
        entries = skill_registry.registry_view()["entries"]
        for name, expected in {"motion:depth-small": "adapter_contract_only", "motion:vmaf": "unavailable",
                               "media:freesound": "not_run", "media:remotion": "historical_pass",
                               "media:real-sfx": "catalogued", "media:real-sfx-cues": "historical_pass"}.items():
            self.assertEqual(entries[name]["test"]["status"], expected)
        for upstream, local in [("motion:animefx", "media:opening-presets"),
                                ("motion:parallax-studio", "media:local-parallax")]:
            self.assertIsNone(entries[upstream]["adapter"])
            self.assertIsNotNone(entries[local]["adapter"])
        for row in entries.values():
            self.assertFalse(row["security"]["authorizes_execution"])
            if alternative := row["alternative"]:
                self.assertIn(alternative, entries)
                self.assertNotEqual(alternative, row["id"])

    def test_shared_and_legacy_skill_can_coexist_without_downloading(self):
        entries = skill_registry.registry_view()["entries"]
        for name, discovery in [("turk-history-documentary", "shared"), ("tarih-icerik", "legacy")]:
            row = entries[f"local:{name}"]
            self.assertEqual(row["source"]["discovery"], discovery)
            self.assertEqual(Path(row["source"]["path"]).parent.name, name)
            self.assertEqual(row["license"]["code"], skill_registry.NO_LICENSE)
            self.assertIsNone(row["adapter"])

    def test_reader_never_executes_adapter_and_returns_a_private_copy(self):
        skill_registry._inventory.cache_clear()
        with (patch("scripts.media_tools.discover", side_effect=AssertionError("network")),
              patch("subprocess.Popen", side_effect=AssertionError("exec"))):
            view = skill_registry.registry_view("tarih", 13)
        view["entries"]["motion:animefx"]["adapter"] = "untrusted executable"
        self.assertIsNone(skill_registry.registry_view("tarih", 13)["entries"]["motion:animefx"]["adapter"])
        self.assertEqual(list(view["experts"]), ["tarih:13"])

    def test_adapter_reference_rejects_shell_and_paths_outside_the_repository(self):
        for reference in ("bash -c echo", "../scripts/create_reel.py", "https://example.invalid/evil.py",
                          "scripts/create_reel.py:render_reel;echo", "scripts/missing.py"):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                skill_registry._adapter_path(reference)

    def test_cli_outputs_brand_filtered_json_and_rejects_unknown_roles(self):
        arguments = ["skill_registry", "--brand", "bakim", "--role"]
        with patch("sys.argv", [*arguments, "20"]), redirect_stdout(StringIO()) as output:
            skill_registry.main()
        data = json.loads(output.getvalue())
        self.assertEqual(list(data["experts"]), ["bakim:20"])
        self.assertIn("motion:vmaf", data["entries"])
        with (patch("sys.argv", [*arguments, "24"]), redirect_stderr(StringIO()) as error,
              self.assertRaises(SystemExit) as failure):
            skill_registry.main()
        self.assertNotEqual(failure.exception.code, 0)
        self.assertIn("Unknown registry brand or role", error.getvalue())
