"""Parse every downloaded source and write the corpus.

Run:  python -m soc_assistant.ingest.build      (or `make corpus`)

Outputs (in data/processed/):
  docs.jsonl    one line per Document
  chunks.jsonl  one line per Chunk (this is what gets indexed)
"""

from __future__ import annotations

from pathlib import Path

from soc_assistant.config import PROJECT_ROOT, load_config
from soc_assistant.ingest.attack import parse_attack
from soc_assistant.ingest.chunking import chunk_document
from soc_assistant.ingest.documents import write_jsonl
from soc_assistant.ingest.playbooks import parse_markdown_source, parse_pdf_source
from soc_assistant.ingest.sources import load_sources


def processed_dir() -> Path:
    return PROJECT_ROOT / load_config()["paths"]["processed"]


def build_documents():
    docs = []
    for src in load_sources():
        if not src.raw_dir.exists():
            raise SystemExit(f"Missing {src.raw_dir}. Run `make data` first.")
        if src.kind == "attack_stix":
            new = [d for p in sorted(src.raw_dir.rglob("*.json"))
                   for d in parse_attack(p, src.id, src.license)]
            skipped = []
        elif src.kind == "markdown":
            new, skipped = parse_markdown_source(src)
        elif src.kind == "pdf":
            new, skipped = parse_pdf_source(src)
        else:
            raise ValueError(f"Unknown source kind: {src.kind}")
        print(f"{src.id:14s} {len(new):4d} docs" + (f"  ({len(skipped)} template stubs skipped)" if skipped else ""))
        docs += new
    ids = [d.doc_id for d in docs]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise SystemExit(f"Duplicate doc_id(s): {dupes}")
    return docs


def main() -> None:
    cfg = load_config()["chunking"]
    docs = build_documents()
    chunks = [c for d in docs for c in chunk_document(d, cfg["chunk_size"], cfg["chunk_overlap"])]
    out = processed_dir()
    write_jsonl(docs, out / "docs.jsonl")
    write_jsonl(chunks, out / "chunks.jsonl")
    avg = sum(len(c.text) for c in chunks) / max(len(chunks), 1)
    print(f"total          {len(docs):4d} docs -> {len(chunks)} chunks (avg {avg:.0f} chars) in {out}")


if __name__ == "__main__":
    main()
