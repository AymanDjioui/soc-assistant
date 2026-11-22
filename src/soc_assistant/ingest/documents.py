"""Shared data types for the knowledge base.

A *Document* is one logical unit we can cite (one ATT&CK technique, one playbook).
A *Chunk* is a piece of a document small enough to fit several into the LLM prompt.
Retrieval returns chunks; evaluation scores documents (doc_id), so chunking can be
re-tuned without relabelling the evaluation questions.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ATT&CK technique IDs such as T1059 or T1059.001.
TECHNIQUE_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")


@dataclass
class Document:
    doc_id: str          # stable, e.g. "attack:T1059.001" or "counteractive:playbook-ransomware"
    title: str
    text: str            # markdown-like text: "## Section" headings separate sections
    source_id: str
    url: str
    license: str
    technique_ids: list[str] = field(default_factory=list)


@dataclass
class Chunk:
    chunk_id: str        # f"{doc_id}#{n}", stable for the same input and settings
    doc_id: str
    title: str
    section: str
    text: str            # includes the "Title > Section" header line
    source_id: str
    url: str
    license: str
    technique_ids: list[str] = field(default_factory=list)


def find_techniques(text: str) -> list[str]:
    return sorted(set(TECHNIQUE_RE.findall(text)))


def write_jsonl(items, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(asdict(it), ensure_ascii=False) + "\n")


def read_jsonl(path: Path, cls):
    with open(path, encoding="utf-8") as f:
        return [cls(**json.loads(line)) for line in f if line.strip()]
