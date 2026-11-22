"""Load `config.yaml` once and expose it as a plain dict."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"


@lru_cache(maxsize=None)
def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
