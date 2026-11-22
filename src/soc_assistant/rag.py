"""The question-answering pipeline: retrieve -> build prompt -> stream the LLM answer.

Week 1 keeps it to the core RAG loop. Later weeks add, in this order, the injection
guard before retrieval (week 3), the refusal gate on weak retrieval and the citation
validator after generation (week 2).
"""

from __future__ import annotations

from collections.abc import Iterator

from soc_assistant.config import load_config
from soc_assistant.llm.client import LLMClient
from soc_assistant.llm.prompts import build_messages
from soc_assistant.retrieval.hybrid import Hit, Retriever


class RagPipeline:
    def __init__(self, retriever: Retriever | None = None, llm: LLMClient | None = None):
        self.cfg = load_config()["retrieval"]
        self.retriever = retriever or Retriever()
        self.llm = llm or LLMClient()

    def retrieve(self, question: str, k: int | None = None, mode: str | None = None) -> list[Hit]:
        return self.retriever.search(question, k=k or self.cfg["top_k"], mode=mode or self.cfg["mode"])

    def stream_answer(self, question: str, hits: list[Hit]) -> Iterator[str]:
        return self.llm.chat(build_messages(question, hits), stream=True)

    def answer(self, question: str, **kw) -> tuple[str, list[Hit]]:
        hits = self.retrieve(question, **kw)
        return "".join(self.stream_answer(question, hits)), hits
