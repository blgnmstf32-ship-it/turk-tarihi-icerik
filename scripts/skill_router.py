"""Select a small, task-specific set of reviewed knowledge notes."""
from __future__ import annotations

from dataclasses import dataclass

from scripts.skill_registry import ROSTERS, registry_view

MAX_NOTES = 2
MAX_NOTE_CHARS = 640
SCENES = {
    "2d": "flat", "battle_map": "map", "atlantic_atlas": "map", "siege_city": "city",
    "city_flyover": "city", "artifact_gears": "mechanism", "layer_diagram": "diagram",
}
ROLE_TASKS = {("bakim", 6): "competitor", ("bakim", 11): "story-sequence",
              ("tarih", 8): "speech", ("bakim", 16): "speech",
              ("tarih", 19): "calendar", ("tarih", 21): "visuals", ("tarih", 22): "visuals",
              ("tarih", 23): "render-plan", ("tarih", 24): "media-review",
              ("tarih", 3): "document-evidence", ("tarih", 4): "document-evidence",
              ("tarih", 5): "document-evidence", ("tarih", 18): "document-evidence",
              ("bakim", 4): "document-evidence", ("bakim", 5): "document-evidence",
              ("bakim", 7): "trend", ("bakim", 20): "document-evidence"}
TASK_NOTES = {
    "hook": ("instagram:hook-delivery",),
    "story": ("instagram:spoken-beat-estimate", "openmontage:storyboard"),
    "speech": ("gemini:tts", "instagram:spoken-turkish-edit"),
    "audio": ("cinecode:sound-perspective", "openmontage:media-synchronization"),
    "edit": ("cinecode:camera-cut-continuity", "openmontage:media-synchronization"),
    "visuals": ("openmontage:scene-tool-fit", "cinecode:preview-depth"),
    "media-review": ("cinecode:preflight-frame-sampling", "gemini:multimodal"),
    "render-plan": ("openmontage:render-provenance", "openmontage:selective-recovery"),
    "topic": ("instagram:calendar-angle-balance", "last30days:trend-window", "research:google-trends-rss"),
    "trend": ("research:google-trends-rss", "last30days:trend-window"),
    "document-evidence": ("factual-research:claim-passage", "open-research:evidence-scope"),
    "rights": ("factual-research:claim-passage",),
    "discovery": ("instagram:caption-collapsed-preview",),
    "competitor": ("instagram:competitor-relative-baseline",),
    "measurement": ("instagram:audit-stage-evidence",),
    "calendar": ("instagram:calendar-angle-balance",),
    "story-sequence": ("instagram:story-sequence",),
    "repurpose": ("instagram:source-extract-repurpose",),
    "provider-config": ("gemini:model-selection", "gemini:api"),
    "validate-json": ("gemini:structured-json",),
    "context-review": ("gemini:context",),
    "cache-review": ("openmontage:cache-revalidation", "gemini:cache"),
    "coordination": ("openmontage:specialist-coordination", "openmontage:production-handoffs"),
    "image-review": ("gemini:multimodal", "gemini:image-generation"),
    "reference-review": ("cinecode:reference-form", "openmontage-15f:reference-shot-log"),
    "spoken-edit": ("instagram:spoken-turkish-edit",),
    "failure-diagnosis": ("superpowers:isolate-failure",),
    "task-handoff": ("matt-pocock:handoff-readiness",),
    "acceptance-review": ("addy-osmani:acceptance-proof",),
    "local-preview-review": ("anthropic:mobile-preview-check",),
    "ci-review": ("openai:ci-evidence",),
    "pause-analysis": ("auto-editor:pause-evidence",),
    "video-quality": ("cinecode:preflight-frame-sampling", "openmontage:selective-recovery"),
    "archive-review": ("openmontage-15f:archive-shot-evidence",),
    "sound-review": ("openmontage-15f:sound-cause",),
}
SCENE_NOTES = {
    ("shotcraft-review", "flat"): ("shotcraft-15h:readable-detail-triplet", "shotcraft-15h:cut-event-drift"),
    ("shotcraft-review", "collage"): ("shotcraft-15h:tabletop-reframe", "shotcraft-15h:cut-event-drift"),
    ("shotcraft-review", "map"): ("shotcraft-15h:svg-path-draw",),
    ("shotcraft-review", "mechanism"): ("shotcraft-15h:readable-detail-triplet", "shotcraft-15h:svg-path-draw"),
    ("shotcraft-review", "diagram"): ("shotcraft-15h:svg-path-draw",),
    ("shotcraft-review", "macro"): ("shotcraft-15h:cut-event-drift",),
    ("shotcraft-review", "science"): ("shotcraft-15h:svg-path-draw",),
    ("shotcraft-review", "motion"): ("shotcraft-15h:cut-event-drift",),
    ("shot-review", "flat"): ("openmontage-15f:evidence-insert",),
    ("shot-review", "collage"): ("openmontage-15f:evidence-insert", "openmontage-15f:archive-shot-evidence"),
    ("shot-review", "map"): ("openmontage-15f:camera-depth-reveal", "openmontage-15f:progressive-graphics"),
    ("shot-review", "city"): ("openmontage-15f:camera-depth-reveal", "openmontage-15f:archive-shot-evidence"),
    ("shot-review", "mechanism"): ("openmontage-15f:pose-to-pose", "openmontage-15f:evidence-insert"),
    ("shot-review", "diagram"): ("openmontage-15f:progressive-graphics", "openmontage-15f:pose-to-pose"),
    ("shot-review", "macro"): ("openmontage-15f:surface-exposure", "openmontage-15f:camera-depth-reveal"),
    ("shot-review", "barrier"): ("openmontage-15f:pose-to-pose", "openmontage-15f:surface-exposure"),
    ("shot-review", "science"): ("openmontage-15f:progressive-graphics", "openmontage-15f:evidence-insert"),
    ("shot-review", "motion"): ("openmontage-15f:progressive-graphics",),
    ("visuals", "map"): ("openmontage:storyboard", "cinecode:camera-cut-continuity"),
    ("visuals", "city"): ("cinecode:camera-cut-continuity",),
    ("visuals", "mechanism"): ("cinecode:preview-depth",),
    ("visuals", "diagram"): ("cinecode:motivated-light", "openmontage:storyboard"),
    ("edit", "collage"): ("cinecode:reference-form",),
    ("edit", "diagram"): ("cinecode:preflight-frame-sampling",),
    ("craft-review", "mechanism"): ("blender-skills:silhouette-budget",),
    ("craft-review", "city"): ("blender-skills:silhouette-budget", "blender-skills:material-light-check"),
    ("craft-review", "diagram"): ("blender-skills:silhouette-budget", "blender-skills:material-light-check"),
    ("craft-review", "barrier"): ("blender-skills:material-light-check",),
    ("craft-review", "macro"): ("video-shotcraft:product-detail-hold", "blender-skills:material-light-check"),
    ("craft-review", "collage"): ("lemo-opuscar:briefing-board-focus", "rough-js:seeded-sketch-strokes"),
    ("craft-review", "science"): ("rough-js:seeded-sketch-strokes",),
    ("foley-review", "collage"): ("earshot:material-contact-cue",),
    ("foley-review", "mechanism"): ("earshot:material-contact-cue",),
    ("foley-review", "macro"): ("earshot:material-contact-cue",),
}
TOPIC_NOTES = {("tarih", "story", "mekanizma"): ("instagram:source-extract-repurpose",),
               ("bakim", "story", "rutin"): ("instagram:spoken-turkish-edit",)}


@dataclass(frozen=True)
class RouteContext:
    brand: str
    role_id: int
    task: str
    scene: str = "general"
    category: str = ""

    def entries(self):
        if self.brand not in ROSTERS or type(self.role_id) is not int:
            raise ValueError("Unknown routing brand or expert")
        return registry_view(self.brand, self.role_id)["entries"]


def specialist_context(role, brand, topic=None):
    topic = topic or {}
    category = topic.get("category", "")
    scene = SCENES.get(topic.get("visual_mode"), "general")
    if scene == "general" and topic.get("id") == "piri-reis-kayip-kaynak" and brand == "tarih":
        scene = "map"
    if scene == "general" and category in {"arsiv", "belge", "etiket", "ambalaj"}:
        scene = "collage"
    role_id = role.get("id")
    task = ROLE_TASKS.get((brand, role_id), role.get("reels_review", {}).get("technique", "general"))
    return RouteContext(brand, role_id, task, scene, category)


def select_knowledge(context):
    """Filter by role and task before ranking by matching scene and topic."""
    entries = context.entries()
    ranked = (
        (SCENE_NOTES.get((context.task, context.scene), ()), "task_scene_match"),
        (TOPIC_NOTES.get((context.brand, context.task, context.category), ()), "task_topic_match"),
        (TASK_NOTES.get(context.task, ()), "task_match"),
    )
    selected = {}
    remaining = MAX_NOTE_CHARS
    for candidates, reason in ranked:
        for identifier in candidates:
            if len(selected) == MAX_NOTES:
                return list(selected.values())
            row = entries.get(identifier)
            if (identifier in selected or not row or row["kind"] != "knowledge" or row["adapter"]
                    or row["security"]["status"] != "curated_reference_only"
                    or row["license"]["scope"] != "upstream_reference"
                    or row["test"]["status"] != "guidance_contract_only"
                    or row["cost"]["metered_or_paid_allowed"] or len(row["task"]) > remaining):
                continue
            selected[identifier] = {"id": identifier, "guidance": row["task"], "reason": reason}
            remaining -= len(row["task"])
    return list(selected.values())
