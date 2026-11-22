"""Phase 0 check: is the LLM reachable, and how fast is it on this machine?

Usage:  python scripts/smoke_llm.py
"""

from __future__ import annotations

import sys
import time

import requests

from soc_assistant.llm.client import LLMClient

PROMPT = [
    {"role": "system", "content": "You are a concise SOC assistant."},
    {"role": "user", "content": "In 3 bullet points: what is MITRE ATT&CK technique T1059.001?"},
]


def main() -> int:
    client = LLMClient()
    print(f"provider={client.provider}  model={client.model}\n")
    start = time.perf_counter()
    first_token_at = None
    pieces = 0
    try:
        for piece in client.chat(PROMPT):
            if first_token_at is None:
                first_token_at = time.perf_counter()
            pieces += 1
            print(piece, end="", flush=True)
    except requests.ConnectionError:
        print("Cannot reach the LLM. Is Ollama running? Try: ollama serve")
        return 1
    except requests.HTTPError as e:
        print(f"LLM returned an error: {e}\nDid you pull the model? Try: ollama pull {client.model}")
        return 1
    total = time.perf_counter() - start
    ttft = (first_token_at or time.perf_counter()) - start
    gen = max(total - ttft, 1e-9)
    print(f"\n\ntime to first token: {ttft:.1f}s | total: {total:.1f}s | ~{pieces / gen:.1f} tokens/s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
