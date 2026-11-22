import json

from soc_assistant.ingest.attack import clean, parse_attack
from soc_assistant.ingest.chunking import chunk_document, pack, split_sections
from soc_assistant.ingest.documents import Document
from soc_assistant.ingest.playbooks import parse_markdown_source
from soc_assistant.ingest.sources import Source


def _technique(stix_id, ext_id, name, **extra):
    return {"type": "attack-pattern", "id": stix_id, "name": name, "description": "Desc of " + name,
            "external_references": [{"source_name": "mitre-attack", "external_id": ext_id,
                                     "url": f"https://attack.mitre.org/techniques/{ext_id}"}],
            "kill_chain_phases": [{"kill_chain_name": "mitre-attack", "phase_name": "execution"}],
            **extra}


def test_attack_parser_skips_revoked_and_deprecated(tmp_path):
    objects = [
        {"type": "x-mitre-tactic", "id": "x-mitre-tactic--1", "name": "Execution", "x_mitre_shortname": "execution"},
        _technique("attack-pattern--live", "T1001", "Live"),
        _technique("attack-pattern--rev", "T1002", "Revoked", revoked=True),
        _technique("attack-pattern--dep", "T1003", "Deprecated", x_mitre_deprecated=True),
        {"type": "course-of-action", "id": "course-of-action--ok", "name": "Good Mitigation",
         "description": "generic", "external_references": [{"source_name": "mitre-attack", "external_id": "M1000"}]},
        {"type": "course-of-action", "id": "course-of-action--old", "name": "Old Mitigation", "x_mitre_deprecated": True,
         "description": "old", "external_references": [{"source_name": "mitre-attack", "external_id": "M1001"}]},
        {"type": "relationship", "id": "relationship--1", "relationship_type": "mitigates",
         "source_ref": "course-of-action--ok", "target_ref": "attack-pattern--live", "description": "Specific advice."},
        {"type": "relationship", "id": "relationship--2", "relationship_type": "mitigates",
         "source_ref": "course-of-action--old", "target_ref": "attack-pattern--live", "description": "Stale advice."},
    ]
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps({"objects": objects}))
    docs = parse_attack(path)
    assert [d.doc_id for d in docs] == ["attack:T1001"]
    text = docs[0].text
    assert "Tactics: Execution" in text
    assert "M1000 Good Mitigation: Specific advice." in text   # relationship text preferred
    assert "Stale advice" not in text                          # deprecated mitigation dropped


def test_clean_removes_citations_links_and_tags():
    raw = "Use <code>powershell -enc</code> (Citation: Foo 2020) see [docs](https://x.y)."
    assert clean(raw) == "Use powershell -enc see docs."


def test_stub_templates_are_skipped(tmp_path):
    template = "## Playbook: X\n\n### Investigate\n\n`TODO: expand`\n\n### Remediate\n\nGeneric remediation advice line.\n"
    for name in ("stub-a", "stub-b"):
        (tmp_path / f"{name}.md").write_text(template)
    real = template + "\n".join(f"Specific ransomware step number {i} with details." for i in range(60))
    (tmp_path / "real.md").write_text(real)
    src = Source(id="t", name="t", repo="o/r", commit="abc", include=["*.md"], kind="markdown",
                 license="MIT", raw_root=str(tmp_path))
    docs, skipped = parse_markdown_source(src)
    assert [d.doc_id for d in docs] == ["t:real"]
    assert sorted(skipped) == ["stub-a.md", "stub-b.md"]
    assert "TODO" not in docs[0].text


def test_sections_split_on_repeated_heading_level():
    text = "# Title\n\nintro\n\n## A\n\nalpha\n\n### sub\n\nbeta\n\n## B\n\ngamma"
    names = [n for n, _ in split_sections(text)]
    assert names == ["Title", "A", "B"]     # "### sub" is below the split level: kept as text


def test_pack_respects_size_and_keeps_numbered_lists():
    body = "\n".join(f"    1. Step {i} do something useful here." for i in range(40))
    pieces = pack(body, size=300, overlap=50)
    assert len(pieces) > 1
    assert all(len(p) <= 300 + 50 + 5 for p in pieces)
    assert not any(p.strip() == "1." for piece in pieces for p in piece.splitlines())


def test_chunk_ids_are_stable_and_headers_present():
    doc = Document(doc_id="x:doc", title="Doc Title", text="## Section A\n\n" + "word " * 400 + "\n\n## Section B\n\n" + "other " * 60,
                   source_id="x", url="u", license="MIT")
    a, b = chunk_document(doc, 300, 50), chunk_document(doc, 300, 50)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b] == [f"x:doc#{i}" for i in range(len(a))]
    assert a[0].text.startswith("Doc Title > Section A\n")
    assert a[-1].text.startswith("Doc Title > Section B\n")
