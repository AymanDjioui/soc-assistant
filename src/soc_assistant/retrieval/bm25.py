"""Keyword search with BM25.

BM25 scores a chunk higher when it contains the query's words, especially rare words
(a term that appears in few chunks, like "mimikatz", counts more than "file"), with a
penalty for very long chunks. It is fast, needs no model, and is very good at exact
identifiers such as technique IDs, which embedding models often blur.
"""

from __future__ import annotations

import re

import numpy as np
from rank_bm25 import BM25Okapi

from soc_assistant.ingest.documents import Chunk

# A technique ID like "T1059.001" must stay ONE token (a plain \w+ split would give
# "t1059" and "001"). Other tokens are runs of letters/digits.
_TOKEN = re.compile(r"t\d{4}(?:\.\d{3})?|[a-z0-9]+")
STOPWORDS = frozenset(
    "a an and are as at be by can do does for from has have how i if in into is it its "
    "may of on or our should so such than that the their then there these this to was "
    "we what when where which who why will with you your".split()
)


def tokenize(text: str) -> list[str]:
    tokens = []
    for tok in _TOKEN.findall(text.lower()):
        if tok in STOPWORDS:
            continue
        tokens.append(tok)
        if tok.startswith("t") and "." in tok:
            tokens.append(tok.split(".")[0])   # "t1059.001" also matches a search for "t1059"
    return tokens


class BM25Index:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(c.text) for c in chunks])

    def search(self, query: str, k: int = 30) -> list[tuple[int, float]]:
        """Return (chunk index, BM25 score) pairs, best first."""
        scores = self.bm25.get_scores(tokenize(query))
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top if scores[i] > 0]
