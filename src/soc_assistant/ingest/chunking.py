"""Split Documents into Chunks.

Two steps:
  1. Split on headings. The split level is the highest heading level that appears at
     least twice; headings at that level or above start a new section, deeper ones are
     kept inside the section as text.
  2. Pack paragraphs of each section greedily up to `chunk_size` characters. Each new
     chunk starts with the last ~`chunk_overlap` characters of the previous one, so a
     sentence cut at a boundary still appears whole in one of the two chunks.

Every chunk text begins with "Title > Section" so that a chunk read on its own (by the
embedder, BM25 or the LLM) still says what it is about.
"""

from __future__ import annotations

import re
from collections import Counter

from soc_assistant.ingest.documents import Chunk, Document, find_techniques

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_SENTENCE = re.compile(r"(?<=[A-Za-z)\]\"'][.!?])\s+")
MIN_CHUNK_CHARS = 40
MIN_SECTION_CHARS = 200   # smaller sections are merged into the next one


def split_sections(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    levels = Counter(len(m.group(1)) for l in lines if (m := _HEADING.match(l)))
    repeated = [lvl for lvl, n in levels.items() if n >= 2]
    split_level = min(repeated) if repeated else 0

    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in lines:
        m = _HEADING.match(line)
        if m and len(m.group(1)) <= split_level:
            sections.append((m.group(2).strip(), []))
        elif m:
            sections[-1][1].append(m.group(2).strip() + ":")   # sub-heading kept as text
        else:
            sections[-1][1].append(line)
    return [(name, "\n".join(body).strip()) for name, body in sections if "\n".join(body).strip()]


def _split_long_line(line: str, size: int) -> list[str]:
    """Sentences first, then words, for a single line longer than `size`."""
    out, cur = [], ""
    for part in _SENTENCE.split(line):
        words = [part] if len(part) <= size else part.split()
        for w in words:
            if cur and len(cur) + 1 + len(w) > size:
                out.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}" if cur else w
    if cur:
        out.append(cur)
    return out


def _pieces(paragraph: str, size: int) -> list[str]:
    """Break a paragraph longer than `size` on line breaks (keeps lists intact),
    falling back to sentences/words only for a single over-long line."""
    if len(paragraph) <= size:
        return [paragraph]
    out, cur = [], ""
    for line in paragraph.split("\n"):
        for seg in ([line] if len(line) <= size else _split_long_line(line, size)):
            if cur and len(cur) + 1 + len(seg) > size:
                out.append(cur)
                cur = seg
            else:
                cur = f"{cur}\n{seg}" if cur else seg
    if cur:
        out.append(cur)
    return out


def _tail(text: str, n: int) -> str:
    if n <= 0 or len(text) <= n:
        return "" if n <= 0 else text
    cut = text[-n:]
    space = cut.find(" ")
    return cut[space + 1:] if space != -1 else cut


def pack(body: str, size: int, overlap: int) -> list[str]:
    units: list[str] = []
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if para:
            units += _pieces(para, size)

    chunks, cur = [], ""
    for u in units:
        if cur and len(cur) + 2 + len(u) > size:
            chunks.append(cur)
            tail = _tail(cur, overlap)
            cur = f"{tail} … {u}" if tail else u
        else:
            cur = f"{cur}\n\n{u}" if cur else u
    if cur:
        chunks.append(cur)
    return chunks


def chunk_document(doc: Document, chunk_size: int = 800, chunk_overlap: int = 120) -> list[Chunk]:
    chunks, carry = [], ""
    sections = split_sections(doc.text)
    for i, (section, body) in enumerate(sections):
        if len(body) < MIN_SECTION_CHARS and i < len(sections) - 1:
            carry += (f"{section}:\n{body}" if section else body) + "\n\n"
            continue
        body, carry = carry + body, ""
        for piece in pack(body, chunk_size, chunk_overlap):
            if len(piece) < MIN_CHUNK_CHARS:
                continue
            header = f"{doc.title} > {section}" if section and section != doc.title else doc.title
            text = f"{header}\n{piece}"
            chunks.append(Chunk(
                chunk_id=f"{doc.doc_id}#{len(chunks)}", doc_id=doc.doc_id, title=doc.title,
                section=section, text=text, source_id=doc.source_id, url=doc.url,
                license=doc.license,
                technique_ids=sorted(set(doc.technique_ids) | set(find_techniques(piece))),
            ))
    return chunks
