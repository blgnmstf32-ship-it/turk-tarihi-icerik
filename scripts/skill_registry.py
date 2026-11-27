"""Read-only inventory of repository skills, adapters, and their evidence."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re

from scripts.media_tools import BRAND_ROLES, CAPABILITIES
from scripts.motion_toolkit import ROLE_TECHNIQUES, registry, skill_index

ROOT = Path(__file__).resolve().parents[1]
ROSTERS = {"tarih": "config/agents.json", "bakim": "config/beauty_agents.json"}
NO_LICENSE = "LicenseRef-No-License-Granted"
MODES = {
    "reference": "Yalnız inceleme veya mevcut editoryal yönerge. Kaynak kopyalama ve çalıştırma yok.",
    "asset_reference": "Yalnız doğrulanmış yerel varlığın kaynak, dönem, lisans ve atıf kaydı.",
    "disabled": "Bu depoda devre dışı.",
    "local": "Mevcut iş akışı ve lisans şartları kapsamında, onaylı girdilerle.",
    "optional": "Yalnız ilgili iş akışı aracı açıkça seçerse ve yerel önkoşullar karşılanırsa.",
    "conditional": "Yerel ağırlık/varlık, dosya özeti ve kullanım izni onayından sonra.",
    "embedded": "Mevcut yerel iş akışının parçası; bağımsız çalıştırma seçeneği değil.",
    "public_metadata": "Mevcut ağ izniyle yalnız kamuya açık lisanslı kaynak adayları. Asıl kaynak incelenir.",
    "local_fixture_only": "Açık izinli özgün yerel örnekle sınırlı.",
}
TEST_STATES = {"catalogued", "guidance_contract_only", "adapter_contract_only", "static_scan_pass",
               "historical_pass", "unavailable", "not_run"}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
QUALIFIER = re.compile(r"[a-zA-Z_][a-zA-Z0-9_-]*\Z")


def _read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _id(name):
    result = re.sub(r"[._]+", "-", name.lower())
    if not SLUG.fullmatch(result):
        raise ValueError(f"Invalid registry identifier: {name}")
    return result


def _key(brand, role_id):
    return f"{brand}:{role_id}"


def _roles(assignments):
    return {_key(brand, role) for brand, roles in assignments.items() for role in roles}


def _local_header(path):
    file = ROOT / path
    if file.resolve() != file:
        raise ValueError(f"Unexpected symlink in local Skill: {path}")
    text = file.read_text(encoding="utf-8")
    opening, _, section = text.partition("\n")
    header, end, _ = section.partition("\n---\n")
    if opening != "---" or not end:
        raise ValueError(f"Missing frontmatter: {path}")
    # Read the existing plain scalar fields without loading Markdown or YAML instructions.
    fields = dict(re.findall(r"(?m)^(name|description|license): +([^\n]+)$", header))
    name, description = fields.get("name", ""), fields.get("description", "")
    if name != file.parent.name or not SLUG.fullmatch(name) or len(name) > 64 or not 1 <= len(description) <= 1024:
        raise ValueError(f"Invalid repository Skill metadata: {path}")
    return fields


def _adapter_path(adapter):
    parts = re.split("[:#]", adapter)
    file = ROOT / parts[0]
    if (len(parts) > 2 or (len(parts) == 2 and not QUALIFIER.fullmatch(parts[1]))
            or not re.fullmatch(r"(?:scripts|media_pilot)/[a-zA-Z0-9_]+\.(?:py|mjs)", parts[0])
            or file.resolve() != file or not file.is_file()):
        raise ValueError(f"Unknown adapter reference: {adapter}")
    return parts[0]


def _entry(identifier, task, roles, *, source, license, metadata=None, evidence=None):
    metadata = metadata or {}
    mode = metadata.get("mode", "reference")
    status = metadata.get("test", "catalogued")
    proof = metadata.get("evidence")
    adapter = metadata.get("adapter")
    runnable = mode not in {"reference", "asset_reference", "disabled"}
    if runnable != bool(adapter) or status not in TEST_STATES:
        raise ValueError(f"Invalid adapter or test state: {identifier}")
    if status not in {"catalogued", "not_run"} and not proof:
        raise ValueError(f"Missing test evidence: {identifier}")
    security_status = {
        "reference": "reference_only", "asset_reference": "license_receipt_required", "disabled": "blocked",
    }.get(mode, "existing_adapter_only")
    kind = {"reference": "knowledge", "asset_reference": "asset_reference"}.get(mode, "tool")
    return {
        "id": identifier, "kind": kind,
        "task": task, "expert_ids": sorted(roles), "brands": sorted({r.split(":")[0] for r in roles}),
        "use": {"mode": mode, "conditions": MODES[mode], "note": metadata.get("note")},
        "source": source, "license": license,
        "security": {"status": metadata.get("security", security_status), "authorizes_execution": False},
        "hardware": metadata.get("hardware", "Yalnız metin; özel donanım gerekmez"),
        "cost": {"category": "disabled" if mode == "disabled" else "no_service_fee",
                 "metered_or_paid_allowed": False},
        "adapter": {"file": _adapter_path(adapter), "entrypoint": adapter} if adapter else None,
        "alternative": metadata.get("alternative"),
        "test": {"status": status, "evidence": (evidence or {}).get(proof, proof)},
    }


def _review_notes(namespace, source, test_file):
    if not re.fullmatch(r"[0-9a-f]{40}", source["revision"]):
        raise ValueError(f"{namespace} knowledge source must be pinned to a full Git revision")
    for name, note in source["notes"].items():
        origin = {
            "repository": source["repository"], "revision": source["revision"],
            "path": note["path"] if "path" in note else source["skill_path"],
            "license_path": source.get("license_path", "LICENSE"),
        }
        if "docs" in note:
            origin["docs"] = note["docs"]
        yield _entry(
            f"{namespace}:{_id(name)}", note["task"], _roles(note["role_keys"]),
            source=origin, license={"code": source["license"], "scope": "upstream_reference"},
            metadata={
                "security": "curated_reference_only",
                "test": "guidance_contract_only", "evidence": test_file,
                "note": "Yerel Türkçe inceleme notu. Kaynak dosya ve çalıştırma bileşenleri eklenmedi.",
            },
        )


@lru_cache(maxsize=1)
def _inventory():
    manifest = _read("config/skill_registry.json")
    if manifest["schema_version"] != 1:
        raise ValueError("Unknown Skill Registry schema version")
    catalog = registry()
    if set(manifest["motion"]) != set(catalog["tools"]) or CAPABILITIES.keys() - manifest["media"].keys():
        raise ValueError("Skill Registry coverage differs from the source catalogs")
    evidence = manifest["evidence"]
    entries, review, experts = {}, defaultdict(dict), {}
    editorial_roles, techniques, project_roles = defaultdict(set), defaultdict(set), defaultdict(set)
    media_roles, motion_roles = defaultdict(set), defaultdict(set)

    def add(row):
        identifier = row["id"]
        if identifier in entries or row["alternative"] == identifier:
            raise ValueError(f"Duplicate identifier or self-reference: {identifier}")
        entries[identifier] = row

    for brand, path in ROSTERS.items():
        roster = _read(path)
        ids = {r["id"] for r in roster}
        if len(roster) != len(ids) or ids != set(range(1, 25 if brand == "tarih" else 21)):
            raise ValueError(f"Skill Registry roster IDs do not match: {brand}")
        for role in roster:
            identifier = _key(brand, role["id"])
            experts[identifier] = {"brand": brand, "id": role["id"], "name": role["name"],
                                   "primary": role["id"] <= 20, "entry_ids": []}
            technique = (role.get("reels_review") or {}).get("technique")
            if role["id"] <= 20 or technique:
                editorial_roles[technique].add(identifier)
        for role_id, names in ROLE_TECHNIQUES[brand].items():
            for name in names:
                techniques[name].add(_key(brand, role_id))
        for role_id, tools in BRAND_ROLES[brand].items():
            for tool in tools:
                media_roles[tool].add(_key(brand, role_id))
        for role_id, names in catalog["direction"][brand]["roles"].items():
            for name in names:
                motion_roles[name].add(_key(brand, role_id))

    for path, definition in manifest["local_skills"].items():
        fields = _local_header(path)
        roles = {identifier for identifier, expert in experts.items()
                 if expert["brand"] == definition["brand"] and expert["primary"]}
        add(_entry(f"local:{fields['name']}", fields["description"], roles,
                   source={"path": path, "discovery": definition["discovery"]},
                   license={"code": fields.get("license", NO_LICENSE)},
                   metadata={**definition, "security": "statically_scanned",
                             "test": "static_scan_pass", "evidence": "skill_scan"}, evidence=evidence))
    discovered = {p.relative_to(ROOT).as_posix() for root in (".agents/skills", ".codex/skills", ".gemini/skills")
                  for p in (ROOT / root).glob("*/SKILL.md")}
    if discovered != manifest["local_skills"].keys():
        raise ValueError("Repository Skill inventory differs from discovery folders")

    from scripts.reels_editorial import playbook
    methods = playbook()["techniques"]
    if editorial_roles.keys() - methods.keys():
        raise ValueError("Unknown or missing editorial technique in roster")
    for name, task in methods.items():
        add(_entry(f"editorial:{_id(name)}", task, editorial_roles[name],
                   source={"path": "config/reels_playbook.json", "key": name}, license={"code": NO_LICENSE},
                   metadata={"test": "guidance_contract_only", "evidence": "offline_quality"}, evidence=evidence))

    for namespace, test_file in (("gemini", "tests/test_gemini_skill_notes.py"),
                                 ("openmontage", "tests/test_openmontage_notes.py"),
                                 ("cinecode", "tests/test_cinecode_notes.py"),
                                 ("instagram", "tests/test_instagram_skill_notes.py")):
        for entry in _review_notes(namespace, manifest[f"{namespace}_knowledge"], test_file):
            add(entry)

    research = _read("config/research_registry.json")
    for namespace, source in research["knowledge"].items():
        for entry in _review_notes(namespace, source, "tests/test_research_tools.py"):
            add(entry)
    for namespace, source in _read("config/development_skill_notes.json").items():
        for entry in _review_notes(namespace, source, "tests/test_development_skill_notes.py"):
            add(entry)
    for namespace, source in _read("config/media_craft_notes.json").items():
        for entry in _review_notes(namespace, source, "tests/test_media_craft.py"):
            add(entry)
    add(_entry("media-craft:pause-review", "Kaynak karelerinde sessizlik adaylarını anlatım ve altyazıya göre işaretle.",
               _roles({"tarih": [15, 16], "bakim": [15, 20]}),
               source={"path": "scripts/pause_review.py"}, license={"code": NO_LICENSE},
               metadata={"mode": "local", "adapter": "scripts/pause_review.py:review_pauses",
                         "test": "adapter_contract_only", "evidence": "tests/test_media_craft.py",
                         "note": "Yalnız çağıranın sağladığı sayısal zaman aralıkları. Zaman çizelgesi ve medya değişmez."}))
    add(_entry("quality-lab:local-review", "Ölçüm kapsamını, kare kusurlarını ve sahneye bağlı kaynak notlarını değerlendir.",
               _roles({"tarih": [16, 24], "bakim": [20]}),
               source={"path": "scripts/video_quality_lab.py"}, license={"code": NO_LICENSE},
               metadata={"mode": "local", "adapter": "scripts/video_quality_lab.py:inspect_snapshot",
                         "test": "adapter_contract_only", "evidence": "tests/test_video_quality_lab.py",
                         "note": "Ağsız ve medyasız, yalnız sağlanan timeline ve kanıt verisi."}))
    trends = research["trends"]
    add(_entry("research:google-trends-rss", trends["task"], _roles(trends["role_keys"]),
               source=trends["source"], license={"code": "Google Trends kullanım koşulları", "scope": "upstream_reference"},
               metadata={"security": "curated_reference_only", "test": "guidance_contract_only",
                         "evidence": "tests/test_research_tools.py"}))
    documents = research["trafilatura"]
    add(_entry("research:trafilatura", "Kaydedilmiş HTML içinden kaynak ve konum bilgili kanıt adayları bul.",
               _roles(documents["role_keys"]),
               source={"repository": "adbar/trafilatura", "release": "v2.4.0", "license_path": "LICENSE"},
               license={"code": "Apache-2.0", "scope": "parser_code"}, metadata=documents))

    for pack in skill_index():
        owner, repo = pack["repository"].split("/")
        for row in pack["skills"]:
            adapted = row["decision"] == "adapt"
            roles = techniques[row["name"]] if adapted else set()
            if adapted:
                project_roles[owner].update(roles)
            license_record = {"code": "Apache-2.0" if owner == "jmwdpk" else "MIT",
                              "assets": "Varlık, font, müzik ve paket lisansı yeniden kullanımda ayrıca doğrulanır"}
            add(_entry(f"skill:{_id(owner)}:{_id(repo)}:{_id(row['name'])}", row["note"], roles,
                       source={"repository": pack["repository"], "revision": pack["commit"], "path": row["path"],
                               "decision": row["decision"]}, license=license_record,
                       metadata={"test": "guidance_contract_only", "evidence": "tests/test_motion_toolkit.py"}
                       if adapted else None))

    for name, data in catalog["tools"].items():
        metadata = manifest["motion"][name]
        roles = (motion_roles[name] | project_roles[metadata.get("roles_from")]
                 | _roles(metadata.get("role_keys", {})))
        licenses = {"code": data["code_license"], "weights": data.get("weight_license"),
                    "assets": data.get("asset_license")}
        add(_entry(f"motion:{_id(name)}", data["use"], roles,
                   source={"path": "config/motion_toolkit.json", "key": name, "revision": data["pin"]},
                   license=licenses, metadata=metadata, evidence=evidence))

    for name, metadata in manifest["media"].items():
        task = CAPABILITIES[name] if name in CAPABILITIES else metadata["task"]
        source = {"path": "media_pilot/ARACLAR.md"}
        motion_name = metadata.get("motion_review_name")
        roles = media_roles[name] | _roles(metadata.get("role_keys", {}))
        if motion_name:
            roles |= motion_roles[motion_name]
            source = {"path": "config/motion_toolkit.json", "key": motion_name}
        add(_entry(f"media:{_id(name)}", task, roles, source=source,
                   license={"code": metadata["license"]}, metadata=metadata, evidence=evidence))

    aliases = {metadata["motion_review_name"]: f"media:{_id(name)}" for name, metadata in manifest["media"].items()
               if metadata.get("motion_review_name")}
    for name, roles in media_roles.items():
        if name in CAPABILITIES:
            for role in roles:
                review[role][name] = f"media:{_id(name)}"
    for name, roles in motion_roles.items():
        if catalog["tools"][name]["status"] == "optional":
            for role in roles:
                review[role][name] = aliases.get(name, f"motion:{_id(name)}")

    for identifier, row in entries.items():
        if row["alternative"] and row["alternative"] not in entries:
            raise ValueError(f"Unknown alternative: {identifier}")
        for expert_id in row["expert_ids"]:
            if expert_id not in experts:
                raise ValueError(f"Unknown expert mapping: {identifier} -> {expert_id}")
            experts[expert_id]["entry_ids"].append(identifier)
    for identifier, options in review.items():
        for entry_id in options.values():
            item = entries[entry_id]
            if not item["adapter"] or identifier not in item["expert_ids"]:
                raise ValueError(f"Unavailable review entry: {entry_id}")

    return entries, experts, dict(review)


def registry_view(brand=None, role_id=None):
    """JSON-compatible independent inventory, optionally narrowed to one brand/role."""
    entries, experts, _ = _inventory()
    selected = {key: row for key, row in experts.items()
                if (brand is None or brand == row["brand"]) and (role_id is None or role_id == row["id"])}
    if not selected:
        raise ValueError("Unknown registry brand or role")
    shown = set(entries) if brand is None and role_id is None else {
        entry for expert in selected.values() for entry in expert["entry_ids"]}
    # Return independent rows so callers cannot mutate the cached allowlist.
    return deepcopy({"schema_version": 1, "entries": {key: entries[key] for key in sorted(shown)},
                     "experts": selected})


def editorial_method(technique):
    """Resolve a configured Reels method without sending the inventory to a model."""
    entries, _, _ = _inventory()
    return entries.get(f"editorial:{technique}", {}).get("task")


def review_options(brand, role_id):
    """Legacy model-facing tool names, resolved from reviewed catalog adapters."""
    entries, _, review = _inventory()
    options = review.get(_key(brand, role_id), {})
    return {name: (registry()["tools"][name]["use"] if name in registry()["tools"] else entries[key]["task"])
            for name, key in options.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand", choices=ROSTERS)
    parser.add_argument("--role", type=int)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    if args.role is not None and args.brand is None:
        parser.error("--role requires --brand")
    try:
        result = registry_view(args.brand, args.role)
    except ValueError as exc:
        parser.error(str(exc))
    if args.summary:
        result = {"schema_version": result["schema_version"],
                  "entries": dict(Counter(row["kind"] for row in result["entries"].values())),
                  "experts": dict(Counter(row["brand"] for row in result["experts"].values() if row["primary"])),
                  "auxiliary": sum(not row["primary"] for row in result["experts"].values())}
    print(json.dumps(result, ensure_ascii=False, indent=None if args.summary else 2))


if __name__ == "__main__":
    main()
