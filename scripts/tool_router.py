"""Dispatch reviewed local adapter calls. Registry paths are inventory, never code to load."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from scripts import media_tools, motion_toolkit, pause_review, research_documents, video_quality_lab
from scripts.skill_registry import registry_view

MAX_SNAPSHOT_CHARS = 250_000
ASSET_SCENES = {"general", "map", "city", "mechanism", "diagram", "collage", "flat"}
OPENING_SCENES = {"general", "map", "mechanism", "diagram"}
COMMERCIAL_HINT = re.compile(r"(?:cc0(?: 1\.0)?|public domain|cc by(?:-sa)? [234]\.0)\Z")


@dataclass(frozen=True)
class Binding:
    task: str
    entrypoint: str
    license: str
    mode: str


BINDINGS = {
    "media:wikimedia": Binding("asset-search", "scripts/media_tools.py:discover",
                              "MediaWiki Action API; dosya başına lisans ve atıf", "public_metadata"),
    "media:openverse": Binding("asset-search", "scripts/media_tools.py:discover",
                              "REST v1; varlık başına özgün kaynak lisansı", "public_metadata"),
    "media:opening-presets": Binding("opening-preset", "scripts/motion_toolkit.py:select_opening_effect",
                                   "Yerel kod için açık izin kaydı yok; AnimeFX bağımlılık olarak kullanılmaz",
                                   "optional"),
    "motion:poly-haven": Binding("asset-catalogue", "scripts/motion_cli.py#catalogue", "AGPL-3.0", "optional"),
    "research:trafilatura": Binding("document-evidence", "scripts/research_documents.py:read_snapshot",
                                    "Apache-2.0", "optional"),
    pause_review.TOOL_ID: Binding("pause-analysis", "scripts/pause_review.py:review_pauses",
                                  "LicenseRef-No-License-Granted", "local"),
    video_quality_lab.TOOL_ID: Binding("video-quality", "scripts/video_quality_lab.py:inspect_snapshot",
                                       "LicenseRef-No-License-Granted", "local"),
}
VERIFIED = {"historical_pass", "adapter_contract_only"}


class Unavailable(RuntimeError):
    """Only fixed reason codes are emitted to reports."""


@dataclass(frozen=True)
class MetadataReply:
    payload: dict
    status_code: int = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _discover(identifier, topic, snapshot):
    provider = identifier.split(":")[1]
    endpoint = {"wikimedia": media_tools.COMMONS, "openverse": media_tools.OPENVERSE}[provider]

    def supplied_metadata(url, **_kwargs):
        if url != endpoint:
            raise ValueError("Unexpected metadata endpoint")
        return MetadataReply(snapshot)

    result = media_tools.discover(provider, str(topic.get("title", ""))[:160], get=supplied_metadata)
    if result["status"] == "unavailable":
        raise Unavailable("invalid_metadata_snapshot")
    candidates = result["candidates"][:6]
    if provider == "wikimedia":
        candidates = [row for row in candidates if COMMERCIAL_HINT.fullmatch(row["license"].casefold())]
    if not candidates:
        raise Unavailable("no_eligible_license_candidates")
    fields = ("title", "author", "artist", "license", "license_url", "source", "description_url")
    return {"status": "candidates", "source": "supplied_metadata_snapshot", "live_http": False,
            "original_page_review_required": True,
            "candidates": [{field: value for field in fields if isinstance(value := row.get(field), str)}
                           for row in candidates]}


def _execute(identifier, context, topic, snapshot, parallax):
    if identifier == video_quality_lab.TOOL_ID:
        try:
            return video_quality_lab.inspect_snapshot(snapshot, brand=context.brand)
        except (AttributeError, KeyError, TypeError, ValueError):
            raise Unavailable("invalid_quality_evidence") from None
    if identifier == pause_review.TOOL_ID:
        return pause_review.review_pauses(snapshot)
    if identifier == research_documents.TOOL_ID:
        try:
            return research_documents.read_snapshot(snapshot)
        except research_documents.ResearchInputError as exc:
            raise Unavailable(str(exc)) from None
    if identifier == "media:opening-presets":
        effect = motion_toolkit.select_opening_effect(context.brand, topic, parallax=parallax)
        if effect is None:
            raise Unavailable("no_applicable_preset")
        return {"effect": effect, "media_created": False}
    if identifier == "motion:poly-haven":
        result = motion_toolkit.poly_haven_catalogue(snapshot, kind="models", limit=6)
        if not result["assets"]:
            raise Unavailable("no_catalogue_candidates")
        return {**result, "source": "supplied_metadata_snapshot", "original_page_review_required": True}
    return _discover(identifier, topic, snapshot)


def _blocked(row, binding, context, cpu_available):
    if row["kind"] != "tool":
        return "knowledge_or_asset_reference"
    if row["use"]["mode"] == "disabled":
        return "disabled_by_policy"
    if row["test"]["status"] == "unavailable":
        return "unverified_runtime"
    if not binding or binding.task != context.task:
        return "adapter_not_permitted_for_task"
    if (row["security"]["status"] != "existing_adapter_only" or row["use"]["mode"] != binding.mode
            or (row["adapter"] or {}).get("entrypoint") != binding.entrypoint
            or row["cost"]["category"] != "no_service_fee" or row["cost"]["metered_or_paid_allowed"]):
        return "security_or_cost_policy"
    if row["license"]["code"] != binding.license:
        return "unreviewed_license"
    if row["test"]["status"] not in VERIFIED:
        return "unverified_runtime"
    if cpu_available is not True:
        return "missing_cpu_capability"
    scenes = {"asset-search": ASSET_SCENES, "opening-preset": OPENING_SCENES,
              "asset-catalogue": {"mechanism", "diagram", "city", "map"}, "document-evidence": {"general"},
              "pause-analysis": {"general"}, "video-quality": {"general"}}
    if context.scene not in scenes[context.task]:
        return "scene_not_supported"
    return None


def _priority(context):
    if context.task == "asset-search":
        primary = "media:wikimedia" if context.brand == "tarih" or context.scene == "map" else "media:openverse"
        return [primary]
    return [key for key, rule in BINDINGS.items() if rule.task == context.task]


def run_tool(context, *, topic, state, snapshots=None, preferred=None, cpu_available=True, parallax=False):
    """Operate on trusted caller data. Never pass model output, command lines, or paths."""
    entries = context.entries()
    report = {"brand": context.brand, "role_id": context.role_id, "task": context.task,
              "scene": context.scene, "status": "unavailable", "selected": None,
              "executed_adapter": None, "rejected": [], "attempts": [], "result": None}
    if preferred is not None and not isinstance(preferred, str):
        report["rejected"].append({"id": None, "reason": "unknown_tool"})
        return report
    agenda = [preferred] if preferred is not None else _priority(context)
    if not agenda:
        report["rejected"].append({"id": None, "reason": "no_registered_adapter_for_task"})
        return report
    if type(topic) is not dict or (snapshots is not None and type(snapshots) is not dict):
        report["rejected"].append({"id": None, "reason": "invalid_local_input"})
        return report
    attempted = set()
    while agenda:
        identifier = agenda.pop(0)
        if identifier in attempted:
            continue
        attempted.add(identifier)
        row = entries.get(identifier)
        if not row:
            known = identifier in registry_view()["entries"]
            report["rejected"].append({"id": identifier if known else None, "reason": "role_not_allowed" if known
                                       else "unknown_tool"})
            continue
        binding = BINDINGS.get(identifier)
        block = _blocked(row, binding, context, cpu_available)
        if block:
            report["rejected"].append({"id": identifier, "reason": block})
            # License, security and unsupported-task errors require review, rather than automatic execution.
            if block in {"unverified_runtime", "missing_cpu_capability"} and binding:
                alternative = row["alternative"]
                if alternative in BINDINGS:
                    agenda.append(alternative)
            continue
        snapshot = (snapshots or {}).get(identifier)
        adapter = ("scripts/motion_toolkit.py:poly_haven_catalogue" if identifier == "motion:poly-haven"
                   else binding.entrypoint)
        topic_fields = {key: topic[key] for key in ("id", "title", "visual_mode", "category") if key in topic}

        def execute():
            report["executed_adapter"] = {"id": identifier, "entrypoint": adapter}
            return _execute(identifier, context, topic_fields, snapshot, parallax)

        try:
            if identifier != "media:opening-presets" and type(snapshot) is not dict:
                raise Unavailable("missing_approved_metadata_snapshot")
            inputs = json.dumps([context.brand, context.role_id, context.task, context.scene, identifier,
                                 topic_fields, snapshot, parallax], sort_keys=True, allow_nan=False)
            if len(inputs) > MAX_SNAPSHOT_CHARS:
                raise Unavailable("snapshot_limit_exceeded")
            cache_version = "video-quality:v2" if identifier == video_quality_lab.TOOL_ID else "v1"
            key = f"tool-router:{cache_version}:" + sha256(inputs.encode()).hexdigest()
            result, cached = state.local_tool_once(key, execute)
        except Unavailable as exc:
            report["rejected"].append({"id": identifier, "reason": str(exc)})
        except (TypeError, ValueError, OSError, RecursionError):
            report["rejected"].append({"id": identifier, "reason": "invalid_local_input_or_adapter_unavailable"})
        else:
            report["attempts"].append({"id": identifier, "adapter": adapter, "status": "cache" if cached else "success"})
            report.update(selected={"id": identifier, "reason": "safe_alternative" if report["rejected"] else "task_scene_role_fit",
                                    "evidence": row["test"]["status"]},
                          result=result, status="cache" if cached else "success")
            return report
        if report["executed_adapter"] and report["executed_adapter"]["id"] == identifier:
            report["attempts"].append({"id": identifier, "adapter": adapter, "status": "unavailable"})
        if row["alternative"] in BINDINGS:
            agenda.append(row["alternative"])
    return report
