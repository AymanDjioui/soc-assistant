"""Turn the MITRE ATT&CK STIX bundle into one Document per technique.

STIX is a graph: techniques ("attack-pattern"), mitigations ("course-of-action") and
detection strategies are separate objects linked by "relationship" objects. For each live
technique we gather:
  - header: ID, name, parent technique, tactics, platforms
  - description
  - mitigations   (relationship "mitigates"; its own description is technique-specific)
  - detection     (relationship "detects" -> detection strategy -> analytics)
Revoked or deprecated objects are skipped on both ends of every relationship.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from soc_assistant.ingest.documents import Document

_CITATION = re.compile(r"\(Citation:[^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def clean(text: str) -> str:
    """Remove citation markers, links and HTML tags: noise for BM25 and wasted LLM tokens."""
    text = _CITATION.sub("", text or "")
    text = _MD_LINK.sub(r"\1", text)
    text = _HTML_TAG.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def is_live(obj: dict) -> bool:
    return not obj.get("revoked") and not obj.get("x_mitre_deprecated")


def attack_id(obj: dict) -> tuple[str, str]:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack" and ref.get("external_id"):
            return ref["external_id"], ref.get("url", "")
    return "", ""


def parse_attack(path: Path, source_id: str = "attack", license: str = "") -> list[Document]:
    objects = json.loads(path.read_text(encoding="utf-8"))["objects"]
    by_id = {o["id"]: o for o in objects}

    tactic_names = {o["x_mitre_shortname"]: o["name"] for o in objects
                    if o["type"] == "x-mitre-tactic" and is_live(o)}

    mitigations: dict[str, list[str]] = defaultdict(list)
    detections: dict[str, list[str]] = defaultdict(list)
    for rel in objects:
        if rel["type"] != "relationship" or not is_live(rel):
            continue
        src, tgt = by_id.get(rel["source_ref"]), by_id.get(rel["target_ref"])
        if not src or not tgt or not is_live(src) or not is_live(tgt):
            continue
        kind = rel["relationship_type"]
        if kind == "mitigates" and src["type"] == "course-of-action":
            mid, _ = attack_id(src)
            desc = clean(rel.get("description") or src.get("description", ""))
            mitigations[tgt["id"]].append(f"- {mid} {src['name']}: {desc}")
        elif kind == "detects" and src["type"] == "x-mitre-detection-strategy":
            lines = [f"{src['name']}:"]
            for ref in src.get("x_mitre_analytic_refs", []):
                an = by_id.get(ref)
                if an and is_live(an) and an.get("description"):
                    platforms = ", ".join(an.get("x_mitre_platforms", []))
                    lines.append(f"- ({platforms}) {clean(an['description'])}")
            detections[tgt["id"]].append("\n".join(lines))

    techniques = [o for o in objects if o["type"] == "attack-pattern" and is_live(o)]
    names = {attack_id(t)[0]: t["name"] for t in techniques}

    docs = []
    for t in techniques:
        tid, url = attack_id(t)
        if not tid:
            continue
        title = f"{tid} {t['name']}"
        if t.get("x_mitre_is_subtechnique") and "." in tid:
            parent = tid.split(".")[0]
            title = f"{tid} {names.get(parent, parent)}: {t['name']}"
        tactics = [tactic_names.get(p["phase_name"], p["phase_name"])
                   for p in t.get("kill_chain_phases", []) if p.get("kill_chain_name") == "mitre-attack"]
        parts = [
            f"MITRE ATT&CK technique {title}.",
            f"Tactics: {', '.join(tactics) or 'n/a'}. Platforms: {', '.join(t.get('x_mitre_platforms', [])) or 'n/a'}.",
            "## Description",
            clean(t.get("description", "")),
        ]
        if mitigations.get(t["id"]):
            parts += ["## Mitigations", "\n".join(sorted(mitigations[t["id"]]))]
        if detections.get(t["id"]):
            parts += ["## Detection", "\n\n".join(sorted(detections[t["id"]]))]
        docs.append(Document(
            doc_id=f"{source_id}:{tid}", title=title, text="\n\n".join(parts),
            source_id=source_id, url=url, license=license, technique_ids=[tid],
        ))
    return sorted(docs, key=lambda d: d.doc_id)
