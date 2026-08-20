"""In-memory GitHub client double for hosted board-store tests."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass

from github_client import (
    GitHubConflictError,
    GitHubNotFoundError,
    TreeEntry,
)


@dataclass(frozen=True, slots=True)
class Call:
    method: str
    args: tuple[object, ...]


class FakeGitHubClient:
    """A small deterministic implementation of the GitHub client contract."""

    def __init__(
        self,
        branches: Mapping[str, Mapping[str, bytes | tuple[bytes, str]]],
        *,
        default_branch: str = "main",
        username: str = "climber",
    ) -> None:
        self._branches = {
            name: {
                path: value if isinstance(value, tuple) else (value, self._sha(value))
                for path, value in files.items()
            }
            for name, files in branches.items()
        }
        self._objects = {
            blob_sha: content
            for files in self._branches.values()
            for content, blob_sha in files.values()
        }
        self._heads = {
            name: self._initial_head_sha(name, files)
            for name, files in self._branches.items()
        }
        self._default_branch = default_branch
        self._username = username
        self.calls: list[Call] = []
        self._pull_number = 1

    def get_default_branch(self, token: str) -> str:
        self.calls.append(Call("get_default_branch", (token,)))
        return self._default_branch

    def get_branch_head_sha(self, token: str, branch: str) -> str:
        self.calls.append(Call("get_branch_head_sha", (token, branch)))
        self._files(branch)
        return self._heads[branch]

    def list_branches(self, token: str) -> list[str]:
        self.calls.append(Call("list_branches", (token,)))
        return sorted(self._branches)

    def create_branch(self, token: str, name: str, from_sha: str) -> None:
        self.calls.append(Call("create_branch", (token, name, from_sha)))
        if name in self._branches:
            raise GitHubConflictError("branch already exists")
        source = next(
            (branch for branch, head in self._heads.items() if head == from_sha), None
        )
        if source is None:
            raise GitHubNotFoundError("branch head is not available")
        self._branches[name] = dict(self._files(source))
        self._heads[name] = from_sha

    def get_tree(self, token: str, branch: str) -> tuple[TreeEntry, ...]:
        self.calls.append(Call("get_tree", (token, branch)))
        files = self._files(self._branch_for_ref(branch))
        paths = set(files)
        for path in tuple(files):
            parents = path.split("/")[:-1]
            paths.update(
                "/".join(parents[:index]) for index in range(1, len(parents) + 1)
            )
        return tuple(
            TreeEntry(
                path,
                "blob" if path in files else "tree",
                files[path][1] if path in files else self._tree_sha(path, files),
            )
            for path in sorted(paths)
        )

    def get_blob(self, token: str, sha: str) -> bytes:
        self.calls.append(Call("get_blob", (token, sha)))
        try:
            return self._objects[sha]
        except KeyError as error:
            raise GitHubNotFoundError("blob is not available") from error

    def put_file(
        self,
        token: str,
        path: str,
        branch: str,
        content: bytes,
        message: str,
        sha: str | None,
    ) -> str:
        self.calls.append(
            Call("put_file", (token, path, branch, content, message, sha))
        )
        files = self._files(branch)
        current = files.get(path)
        if current is None and sha is not None:
            raise GitHubConflictError("file changed")
        if current is not None and sha != current[1]:
            raise GitHubConflictError("file changed")
        blob_sha = self._sha(content)
        files[path] = (content, blob_sha)
        self._objects[blob_sha] = content
        commit_sha = self._commit_sha(branch, path, content, message)
        self._heads[branch] = commit_sha
        return commit_sha

    def create_pull_request(
        self, token: str, title: str, head: str, base: str, body: str
    ) -> str:
        self.calls.append(Call("create_pull_request", (token, title, head, base, body)))
        self._files(head)
        self._files(base)
        url = f"https://example.test/pull/{self._pull_number}"
        self._pull_number += 1
        return url

    def get_authenticated_user(self, token: str) -> str:
        self.calls.append(Call("get_authenticated_user", (token,)))
        return self._username

    def file_bytes(self, branch: str, path: str) -> bytes:
        return self._files(branch)[path][0]

    def calls_named(self, method: str) -> tuple[Call, ...]:
        return tuple(call for call in self.calls if call.method == method)

    def _files(self, branch: str) -> dict[str, tuple[bytes, str]]:
        try:
            return self._branches[branch]
        except KeyError as error:
            raise GitHubNotFoundError("branch is not available") from error

    def _branch_for_ref(self, reference: str) -> str:
        if reference in self._branches:
            return reference
        branch = next(
            (name for name, head in self._heads.items() if head == reference), None
        )
        if branch is None:
            raise GitHubNotFoundError("branch head is not available")
        return branch

    def _initial_head_sha(
        self, branch: str, files: Mapping[str, tuple[bytes, str]]
    ) -> str:
        digest = hashlib.sha256()
        digest.update(branch.encode())
        for path, (content, blob_sha) in sorted(files.items()):
            digest.update(path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(content)
            digest.update(blob_sha.encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()

    @staticmethod
    def _sha(content: bytes) -> str:
        return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()

    def _tree_sha(self, path: str, files: Mapping[str, tuple[bytes, str]]) -> str:
        digest = hashlib.sha256(path.encode("utf-8"))
        for child, (content, blob_sha) in sorted(files.items()):
            if child.startswith(f"{path}/"):
                digest.update(child.encode("utf-8"))
                digest.update(content)
                digest.update(blob_sha.encode("utf-8"))
        return digest.hexdigest()

    def _commit_sha(self, branch: str, path: str, content: bytes, message: str) -> str:
        return hashlib.sha256(
            f"{self._heads[branch]}\0{path}\0{message}".encode() + content
        ).hexdigest()
