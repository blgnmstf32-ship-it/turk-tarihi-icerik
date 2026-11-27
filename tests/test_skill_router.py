from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from scripts import media_tools, motion_toolkit, reels_editorial, skill_registry, tool_router
from scripts.ai_agents import run_agents
from scripts.editorial_state import EditorialState
from scripts.skill_router import MAX_NOTE_CHARS, MAX_NOTES, RouteContext, select_knowledge, specialist_context


HISTORY = {"id": "piri-reis-kayip-kaynak", "title": "Piri Reis haritası", "category": "kesif"}
BEAUTY = {"id": "bariyer", "title": "Cilt bariyeri", "visual_mode": "layer_diagram"}


def commons(license_name):
    return {"query": {"pages": {"1": {"title": "File:Reviewed.png", "imageinfo": [{
        "mediatype": "BITMAP", "mime": "image/png", "extmetadata": {
            "Artist": {"value": "Deneme sanatçısı"}, "LicenseShortName": {"value": license_name},
        },
    }]}}}}


def openverse(license_name):
    return {"results": [{"title": "Deneme kaydı", "creator": "Deneme sanatçısı", "license": license_name,
                         "license_url": "https://creativecommons.org/licenses/by/4.0/",
                         "foreign_landing_url": "https://example.org/test-record"}]}


class SkillRoutingTests(unittest.TestCase):
    def test_same_visual_task_selects_history_map_and_beauty_diagram_guidance(self):
        role = {"id": 13, "reels_review": {"technique": "visuals"}}
        history = select_knowledge(specialist_context(role, "tarih", HISTORY))
        beauty = select_knowledge(specialist_context(role, "bakim", BEAUTY))
        self.assertEqual([row["id"] for row in history],
                         ["openmontage:storyboard", "cinecode:camera-cut-continuity"])
        self.assertEqual([row["id"] for row in beauty],
                         ["cinecode:motivated-light", "openmontage:storyboard"])
        self.assertTrue(all(row["reason"] == "task_scene_match" for row in history + beauty))

    def test_topic_specific_selection_and_role_rules_stay_bounded(self):
        picked = select_knowledge(RouteContext("tarih", 7, "story", "mechanism", "mekanizma"))
        self.assertEqual(picked[0]["id"], "instagram:source-extract-repurpose")
        self.assertEqual(picked[0]["reason"], "task_topic_match")
        self.assertLessEqual(len(picked), MAX_NOTES)
        self.assertLessEqual(sum(len(row["guidance"]) for row in picked), MAX_NOTE_CHARS)
        self.assertEqual(select_knowledge(RouteContext("tarih", 6, "competitor")), [])
        self.assertEqual(select_knowledge(RouteContext("bakim", 20, "unknown")), [])

    def test_gemini_notes_reach_audio_role_without_exposing_adapter_or_registry(self):
        role = {"id": 8, "reels_review": {"technique": "audio"}}
        guide = reels_editorial.specialist_guidance(role, "tarih", HISTORY)
        self.assertIn("Charon", guide["skill_notes"][0])
        self.assertEqual([note["id"] for note in select_knowledge(specialist_context(role, "tarih", HISTORY))],
                         ["gemini:tts", "instagram:spoken-turkish-edit"])
        self.assertTrue(all(isinstance(note, str) for note in guide["skill_notes"]))
        self.assertNotIn("runtime", json.dumps(guide))


class LocalToolRoutingTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "editorial.sqlite3"
        self.state = EditorialState(self.path)

    def test_history_routes_to_existing_openverse_adapter_when_commons_has_no_eligible_asset(self):
        context = RouteContext("tarih", 3, "asset-search", "map")
        snapshots = {"media:wikimedia": commons("CC BY 4.0 NC"), "media:openverse": openverse("by")}
        with (patch("requests.sessions.Session.request", side_effect=AssertionError("network")),
              patch.object(media_tools, "discover", wraps=media_tools.discover) as discover):
            report = tool_router.run_tool(context, topic=HISTORY, state=self.state, snapshots=snapshots)
        self.assertEqual([call.args[0] for call in discover.call_args_list], ["wikimedia", "openverse"])
        self.assertEqual(report["selected"]["reason"], "safe_alternative")
        self.assertEqual(report["rejected"], [{"id": "media:wikimedia", "reason": "no_eligible_license_candidates"}])
        self.assertEqual(report["executed_adapter"], {"id": "media:openverse", "entrypoint": "scripts/media_tools.py:discover"})
        self.assertEqual([x["status"] for x in report["attempts"]], ["unavailable", "success"])
        self.assertTrue(report["result"]["original_page_review_required"])
        self.assertFalse(report["result"]["live_http"])

    def test_beauty_prefers_openverse_but_uses_commons_when_snapshot_is_missing(self):
        context = RouteContext("bakim", 12, "asset-search", "diagram")
        snapshots = {"media:wikimedia": commons("CC BY-SA 4.0")}
        report = tool_router.run_tool(context, topic=BEAUTY, state=self.state, snapshots=snapshots)
        self.assertEqual(report["rejected"], [{"id": "media:openverse", "reason": "missing_approved_metadata_snapshot"}])
        self.assertEqual(report["selected"]["id"], "media:wikimedia")
        self.assertEqual([item["id"] for item in report["attempts"]], ["media:wikimedia"])

    def test_opening_preset_is_real_local_adapter_and_stays_separate_by_brand(self):
        examples = (("bakim", 14, "diagram", BEAUTY), ("tarih", 13, "map", HISTORY))
        with patch.object(motion_toolkit, "select_opening_effect", wraps=motion_toolkit.select_opening_effect) as call:
            for brand, role, scene, topic in examples:
                context = RouteContext(brand, role, "opening-preset", scene)
                first = tool_router.run_tool(context, topic=topic, state=self.state)
                reused = tool_router.run_tool(context, topic=topic, state=EditorialState(self.path))
                self.assertEqual(first["result"], {"effect": "lines-reveal", "media_created": False})
                self.assertEqual(reused["status"], "cache")
                self.assertIsNone(reused["executed_adapter"])
                self.assertEqual(reused["result"], first["result"])
        self.assertEqual(call.call_count, 2)
        self.assertEqual(self.state.reserve(40), 1)

    def test_unknown_disabled_unavailable_and_advisory_paths_never_execute(self):
        context = RouteContext("tarih", 14, "opening-preset", "mechanism")
        cases = (
            (context, "unknown-sensitive-text", "unknown_tool"),
            (context, "cinecode:sound-perspective", "knowledge_or_asset_reference"),
            (context, "media:freesound", "disabled_by_policy"),
            (context, "media:earshot", "adapter_not_permitted_for_task"),
            (RouteContext("tarih", 15, "quality", "flat"), "motion:vmaf", "unverified_runtime"),
            (context, "media:opening-presets", "role_not_allowed"),
        )
        with patch.object(tool_router, "_execute", side_effect=AssertionError("execution")):
            for request, tool, reason in cases:
                report = tool_router.run_tool(request, topic=HISTORY, state=self.state, preferred=tool)
                self.assertIsNone(report["executed_adapter"])
                self.assertIsNone(report["result"])
                self.assertEqual(report["rejected"][0]["reason"], reason)
                self.assertNotIn("unknown-sensitive-text", json.dumps(report))

    def test_license_security_and_cpu_gates_precede_even_cached_results(self):
        context = RouteContext("bakim", 14, "opening-preset", "diagram")
        tool_router.run_tool(context, topic=BEAUTY, state=self.state)
        blocked = tool_router.run_tool(context, topic=BEAUTY, state=self.state, cpu_available=False)
        self.assertEqual(blocked["rejected"][0]["reason"], "missing_cpu_capability")
        entries = context.entries()
        row = entries["media:opening-presets"]
        with patch.object(RouteContext, "entries", return_value=entries):
            row["license"]["code"] = "unreviewed"
            blocked = tool_router.run_tool(context, topic=BEAUTY, state=self.state)
            self.assertEqual(blocked["rejected"][0]["reason"], "unreviewed_license")
            row["cost"]["metered_or_paid_allowed"] = True
            blocked = tool_router.run_tool(context, topic=BEAUTY, state=self.state)
            self.assertEqual(blocked["rejected"][0]["reason"], "security_or_cost_policy")
        self.assertIsNone(blocked["executed_adapter"])

    def test_local_catalogue_filters_models_without_running_cli_or_downloading(self):
        context = RouteContext("bakim", 13, "asset-catalogue", "diagram")
        snapshots = {"motion:poly-haven": {"item": {"type": 2, "name": "Fixture"}, "unwanted": {"type": 0}}}
        with patch.object(motion_toolkit, "load_poly_haven", side_effect=AssertionError("live")):
            report = tool_router.run_tool(context, topic=BEAUTY, state=self.state, snapshots=snapshots)
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["executed_adapter"]["entrypoint"], "scripts/motion_toolkit.py:poly_haven_catalogue")
        self.assertEqual([row["id"] for row in report["result"]["assets"]], ["item"])
        self.assertFalse(report["result"]["assets"][0]["downloaded"])

    def test_only_successful_cache_output_survives_and_concurrent_work_runs_once(self):
        context = RouteContext("bakim", 14, "opening-preset", "diagram")
        call = Mock(side_effect=[OSError("private detail"), "lines-reveal"])
        with patch.object(motion_toolkit, "select_opening_effect", call):
            failed = tool_router.run_tool(context, topic=BEAUTY, state=self.state)
            with ThreadPoolExecutor(max_workers=2) as workers:
                reports = list(workers.map(lambda _: tool_router.run_tool(context, topic=BEAUTY, state=self.state), range(2)))
        self.assertEqual(failed["status"], "unavailable")
        self.assertNotIn("private detail", json.dumps(failed))
        self.assertEqual({row["status"] for row in reports}, {"success", "cache"})
        self.assertEqual(call.call_count, 2)

    def test_registry_entries_and_bindings_agree_on_licensed_adapters(self):
        entries = skill_registry.registry_view()["entries"]
        self.assertGreaterEqual(len(entries), 144)
        for identifier, binding in tool_router.BINDINGS.items():
            row = entries[identifier]
            self.assertEqual((row["adapter"]["entrypoint"], row["license"]["code"], row["kind"]),
                             (binding.entrypoint, binding.license, "tool"))

    def test_real_expert_entrypoint_attaches_relevant_brief_and_local_tool_receipt(self):
        agents = json.loads((skill_registry.ROOT / "config/agents.json").read_text(encoding="utf-8"))
        answers = iter((
            {"rationale": "Harita planı", "assignments": [{"role_id": 11, "brief": "Açılış seç"}]},
            {"suggestion": "Belge ayrıntısı", "caveat": "Kaynak kontrolü", "source_numbers": [], "media_tool": None},
            {"rationale": "Uygun", "tradeoff": "Kaynak", "considered_role_ids": [11], "preferred_role_id": 11},
        ))

        def evaluate(_role, _instruction, _prompt, validate, **_kwargs):
            answer, error = validate(json.dumps(next(answers)))
            self.assertIsNone(error)
            return {"status": "proposal", "answer": answer, "actual_llm_used": False}

        session = Mock(calls=0, cached_roles=0, gemini_attempts=0, cloudflare_calls=0)
        session.evaluate.side_effect = evaluate
        with patch.dict("os.environ", {"ENABLE_20_LLM_AGENTS": "1", "OPENROUTER_API_KEY": "fixture"}, clear=True):
            report = run_agents(HISTORY, agents, self.path.parent, brand="tarih", media_review=True,
                                settings={"editorial_intelligence": {"free_llm_enabled": True}},
                                state_path=self.path, gemini_session=session)
        expert_prompt = session.evaluate.call_args_list[1].args[2]
        self.assertEqual(len(expert_prompt["reels_guidance"]["skill_notes"]), 2)
        report_row = next(row for row in report["roles"] if row["role_id"] == 11)
        self.assertEqual(report_row["tool_route"]["executed_adapter"]["id"], "media:opening-presets")
        self.assertEqual(report["calls"], 0)
