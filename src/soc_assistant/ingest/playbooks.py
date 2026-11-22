"""Parse incident-response playbooks (Markdown and PDF) into Documents.

Several public playbook repos contain *templates*: files whose sections are still
"TODO" placeholders. They would pollute retrieval with empty text, so we
  1. drop every line containing "TODO",
  2. measure the text that is unique to the file (lines that appear in several files
     of the same repo are template boilerplate), and
  3. keep the file only if at least `min_unique_chars` of unique text remain.
"""

from __future__ import annotations

import fnmatch
import logging
import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from soc_assistant.ingest.documents import Document, find_techniques
from soc_assistant.ingest.sources import Source

_MD_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
MIN_UNIQUE_CHARS = 1500
logging.getLogger("pypdf").setLevel(logging.ERROR)   # silence harmless PDF xref warnings


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "-", text).strip("-")


def clean_markdown(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if "TODO" in line:
            continue
        line = _HTML_TAG.sub("", _MD_LINK.sub(r"\1", line)).rstrip()
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def markdown_title(text: str, fallback: str) -> str:
    """The first heading is the title only if no other heading shares its level."""
    heads = [(len(m.group(1)), m.group(2)) for l in text.splitlines() if (m := _HEADING.match(l))]
    if heads and sum(1 for lvl, _ in heads if lvl == heads[0][0]) == 1:
        return re.sub(r"^Playbook:\s*", "", heads[0][1]).strip() or fallback
    return fallback


def unique_chars(text: str, line_counts: Counter) -> int:
    """Characters on lines that appear in this file only (not template boilerplate)."""
    return sum(len(l.strip()) for l in text.splitlines() if l.strip() and line_counts[l.strip()] <= 1)


def parse_markdown_source(src: Source, min_unique_chars: int = MIN_UNIQUE_CHARS) -> tuple[list[Document], list[str]]:
    files = sorted(p for p in src.raw_dir.rglob("*.md") if p.is_file()
                   and not any(fnmatch.fnmatch(p.relative_to(src.raw_dir).as_posix(), g) for g in src.exclude))
    cleaned = {p: clean_markdown(p.read_text(encoding="utf-8", errors="replace")) for p in files}
    line_counts = Counter()
    for text in cleaned.values():
        line_counts.update({l.strip() for l in text.splitlines() if l.strip()})

    docs, skipped = [], []
    for path, text in cleaned.items():
        rel = path.relative_to(src.raw_dir).as_posix()
        if unique_chars(text, line_counts) < min_unique_chars:
            skipped.append(rel)
            continue
        title = markdown_title(text, re.sub(r"\s*-\s*", " ", path.stem).strip())
        docs.append(Document(
            doc_id=f"{src.id}:{slug(path.stem)}", title=title, text=text,
            source_id=src.id, url=src.web_url(rel), license=src.license,
            technique_ids=find_techniques(title + " " + path.stem),
        ))
    return docs, skipped


# ---- CERT-SG IRM PDFs -------------------------------------------------------------

IRM_STEPS = {"PREPARATION", "IDENTIFICATION", "CONTAINMENT", "REMEDIATION", "RECOVERY", "LESSONS LEARNED"}
_BULLET = re.compile(r"^\s*(?:[▪•●→]|o\s|-\s)\s*")
_NOISE = re.compile(r"^(TLP:\w+|IRM #\d+.*|\d{1,2})$")


def irm_pdf_to_text(path: Path) -> str:
    """Keep the six incident-handling steps, drop cover/abstract pages and page furniture."""
    pages = [p.extract_text() or "" for p in PdfReader(path).pages]
    start = next((i for i, t in enumerate(pages)
                  if any(l.strip() == "PREPARATION" for l in t.splitlines())), 0)
    out: list[str] = []
    for line in "\n".join(pages[start:]).splitlines():
        line = line.strip()
        if not line or _NOISE.match(line):
            continue
        if line in IRM_STEPS:
            out += ["", f"## {line.title()}", ""]
        elif _BULLET.match(line):
            out.append("- " + _BULLET.sub("", line))
        elif out and out[-1] and not out[-1].startswith("## "):
            out[-1] += " " + line          # re-join lines wrapped by the PDF layout
        else:
            out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def parse_pdf_source(src: Source) -> tuple[list[Document], list[str]]:
    docs = []
    for path in sorted(src.raw_dir.rglob("*.pdf")):
        rel = path.relative_to(src.raw_dir).as_posix()
        m = re.match(r"IRM-(\d+)-(.+)", path.stem)
        num, name = (m.group(1), m.group(2)) if m else ("", path.stem)
        name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name).replace("_", " ").replace("-", " ")
        title = f"CERT-SG IRM #{num}: {name}" if num else name
        docs.append(Document(
            doc_id=f"{src.id}:{slug(path.stem)}", title=title, text=irm_pdf_to_text(path),
            source_id=src.id, url=src.web_url(rel), license=src.license,
        ))
    return docs, []
