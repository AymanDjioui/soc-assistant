"""Build the dense (Chroma) index for one or more embedding models.

Run:  python -m soc_assistant.retrieval.index                 (model from config.yaml)
      python -m soc_assistant.retrieval.index --models A B    (several, for the comparison)
"""

from __future__ import annotations

import argparse
import time

from soc_assistant.config import load_config
from soc_assistant.retrieval.dense import DenseIndex, Embedder
from soc_assistant.retrieval.hybrid import load_chunks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=[load_config()["embeddings"]["model"]])
    args = ap.parse_args()
    chunks = load_chunks()
    for model in args.models:
        t0 = time.time()
        DenseIndex.build(Embedder(model), chunks)
        print(f"{model}: indexed {len(chunks)} chunks in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
