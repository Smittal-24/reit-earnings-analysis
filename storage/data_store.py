"""Shared data store abstraction (section 2): the GitHub repo backing this
app for documents, structured data, watchlist, history, and the Excel
workbook.

Two implementations:
- LocalFileStore: plain filesystem, used for local development and unit
  tests (no network calls).
- GitHubFileStore: commits/reads via the GitHub API (PyGithub), used when
  deployed on Streamlit Community Cloud, where the local filesystem is
  ephemeral and the GitHub repo is the only persistent store.

Everything else in the app should depend on the DataStore protocol, never
directly on pathlib or PyGithub.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol


class DataStore(Protocol):
    def exists(self, path: str) -> bool: ...
    def read_bytes(self, path: str) -> bytes: ...
    def write_bytes(self, path: str, data: bytes, commit_message: str) -> None: ...
    def read_text(self, path: str) -> str: ...
    def write_text(self, path: str, text: str, commit_message: str) -> None: ...
    def read_json(self, path: str) -> dict | list: ...
    def write_json(self, path: str, data: dict | list, commit_message: str) -> None: ...
    def list_dir(self, prefix: str) -> list[str]: ...


class LocalFileStore:
    """Plain-filesystem implementation. Use for local dev and tests."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _full(self, path: str) -> Path:
        return self.root / path

    def exists(self, path: str) -> bool:
        return self._full(path).exists()

    def read_bytes(self, path: str) -> bytes:
        return self._full(path).read_bytes()

    def write_bytes(self, path: str, data: bytes, commit_message: str) -> None:
        full = self._full(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)

    def read_text(self, path: str) -> str:
        return self._full(path).read_text(encoding="utf-8")

    def write_text(self, path: str, text: str, commit_message: str) -> None:
        full = self._full(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(text, encoding="utf-8")

    def read_json(self, path: str) -> dict | list:
        return json.loads(self.read_text(path))

    def write_json(self, path: str, data: dict | list, commit_message: str) -> None:
        self.write_text(path, json.dumps(data, indent=2, default=str), commit_message)

    def list_dir(self, prefix: str) -> list[str]:
        full = self._full(prefix)
        if not full.exists():
            return []
        return sorted(
            str(p.relative_to(self.root)).replace("\\", "/")
            for p in full.rglob("*")
            if p.is_file()
        )


class GitHubFileStore:
    """Commits/reads files via the GitHub API — used when deployed, where
    the shared data store (section 2) is the GitHub repo itself, not any
    local disk."""

    def __init__(self, repo_full_name: str, token: str, branch: str = "main"):
        from github import Github  # PyGithub

        self._gh = Github(token)
        self._repo = self._gh.get_repo(repo_full_name)
        self._branch = branch

    def exists(self, path: str) -> bool:
        try:
            self._repo.get_contents(path, ref=self._branch)
            return True
        except Exception:
            return False

    def read_bytes(self, path: str) -> bytes:
        content_file = self._repo.get_contents(path, ref=self._branch)
        return content_file.decoded_content

    def write_bytes(self, path: str, data: bytes, commit_message: str) -> None:
        try:
            existing = self._repo.get_contents(path, ref=self._branch)
            self._repo.update_file(path, commit_message, data, existing.sha, branch=self._branch)
        except Exception:
            self._repo.create_file(path, commit_message, data, branch=self._branch)

    def read_text(self, path: str) -> str:
        return self.read_bytes(path).decode("utf-8")

    def write_text(self, path: str, text: str, commit_message: str) -> None:
        self.write_bytes(path, text.encode("utf-8"), commit_message)

    def read_json(self, path: str) -> dict | list:
        return json.loads(self.read_text(path))

    def write_json(self, path: str, data: dict | list, commit_message: str) -> None:
        self.write_text(path, json.dumps(data, indent=2, default=str), commit_message)

    def list_dir(self, prefix: str) -> list[str]:
        try:
            contents = self._repo.get_contents(prefix, ref=self._branch)
        except Exception:
            return []
        files = []
        stack = list(contents) if isinstance(contents, list) else [contents]
        while stack:
            item = stack.pop()
            if item.type == "dir":
                stack.extend(self._repo.get_contents(item.path, ref=self._branch))
            else:
                files.append(item.path)
        return sorted(files)