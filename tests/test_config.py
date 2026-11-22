import pytest

from soc_assistant.config import load_config
from soc_assistant.llm.client import LLMClient


def test_config_defaults_are_local():
    cfg = load_config()
    assert cfg["llm"]["provider"] == "ollama", "the demo must run fully local by default"
    assert cfg["retrieval"]["mode"] in {"bm25", "dense", "hybrid"}


def test_unknown_provider_rejected():
    cfg = dict(load_config()["llm"], provider="nope")
    with pytest.raises(ValueError):
        LLMClient(cfg)


def test_api_provider_requires_key(monkeypatch):
    cfg = dict(load_config()["llm"], provider="api")
    monkeypatch.delenv(cfg["api"]["api_key_env"], raising=False)
    with pytest.raises(RuntimeError):
        LLMClient(cfg).complete([{"role": "user", "content": "hi"}])
