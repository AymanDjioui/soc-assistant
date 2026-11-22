"""Read the source manifest (`data/sources.yaml`) and download the pinned files.

Run:  python -m soc_assistant.ingest.sources        (or `make data`)

Each source is a GitHub repo pinned to a commit. We list the repo tree at that commit,
keep the paths matching the `include` globs, and download them to data/raw/<source id>/.
Files already on disk are skipped, so the command is safe to re-run.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

import requests
import yaml

from soc_assistant.config import PROJECT_ROOT, load_config

MANIFEST = PROJECT_ROOT / "data" / "sources.yaml"


@dataclass
class Source:
    id: str
    name: str
    repo: str
    commit: str
    include: list[str]
    kind: str  # attack_stix | markdown | pdf
    license: str
    license_url: str = ""
    exclude: list[str] = field(default_factory=list)
    raw_root: str = ""   # override the download folder (used by tests)

    def raw_url(self, path: str) -> str:
        return f"https://raw.githubusercontent.com/{self.repo}/{self.commit}/{quote(path)}"

    def web_url(self, path: str) -> str:
        """Human-readable link shown in the sources panel."""
        return f"https://github.com/{self.repo}/blob/{self.commit}/{quote(path)}"

    @property
    def raw_dir(self) -> Path:
        if self.raw_root:
            return Path(self.raw_root)
        return PROJECT_ROOT / load_config()["paths"]["raw"] / self.id


def load_sources(path: Path = MANIFEST) -> list[Source]:
    with open(path, encoding="utf-8") as f:
        items = yaml.safe_load(f)
    known = set(Source.__dataclass_fields__)
    return [Source(**{k: v for k, v in it.items() if k in known}) for it in items]


def list_matching(src: Source) -> list[str]:
    url = f"https://api.github.com/repos/{src.repo}/git/trees/{src.commit}?recursive=1"
    tree = requests.get(url, timeout=30).json()["tree"]
    paths = [t["path"] for t in tree if t["type"] == "blob"]
    # fnmatch's "*" also matches "/", so "dir/*/*.md" works as expected for our globs.
    return sorted(p for p in paths
                  if any(fnmatch.fnmatch(p, g) for g in src.include)
                  and not any(fnmatch.fnmatch(p, g) for g in src.exclude))


def download(src: Source) -> int:
    new = 0
    for path in list_matching(src):
        dest = src.raw_dir / path
        if dest.exists() and dest.stat().st_size > 0:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(src.raw_url(path), timeout=120)
        r.raise_for_status()
        dest.write_bytes(r.content)
        new += 1
    return new


def main() -> None:
    for src in load_sources():
        n = download(src)
        total = sum(1 for p in src.raw_dir.rglob("*") if p.is_file())
        print(f"{src.id:14s} {total:4d} files ({n} new)  license: {src.license}")


if __name__ == "__main__":
    main()
