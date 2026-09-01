"""Small typed wrapper around the GitHub REST API used by the workbench."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import socket
import urllib.error
import urllib.request
from typing import Any, Mapping
from urllib.parse import quote


class GitHubError(RuntimeError):
    """A GitHub API request could not be completed."""


class GitHubNotFoundError(GitHubError):
    """The requested GitHub resource does not exist."""


class GitHubConflictError(GitHubError):
    """GitHub rejected the request because the resource changed."""


class GitHubAuthError(GitHubError):
    """The GitHub token is invalid or no longer authorized."""


class GitHubForbiddenError(GitHubError):
    """The GitHub token lacks permission for the request."""


class GitHubRateLimitError(GitHubError):
    """GitHub rejected the request because the rate limit was exhausted."""


class GitHubTransportError(GitHubError):
    """GitHub could not be reached or returned invalid response data."""


@dataclass(frozen=True, slots=True)
class TreeEntry:
    path: str
    type: str
    sha: str


class GitHubClient:
    """Perform the limited GitHub REST operations needed by board publishing."""

    def __init__(
        self, owner: str, repo: str, *, base_url: str = "https://api.github.com"
    ) -> None:
        self._owner = quote(owner, safe="")
        self._repo = quote(repo, safe="")
        self._base_url = base_url.rstrip("/")

    def get_default_branch(self, token: str) -> str:
        payload = self._call(token, "GET", self._repository_path())
        return _required_string(payload, "default_branch")

    def get_branch_head_sha(self, token: str, branch: str) -> str:
        payload = self._call(
            token,
            "GET",
            f"{self._repository_path()}/git/ref/heads/{quote(branch, safe='')}",
        )
        return _required_string(_required_object(payload, "object"), "sha")

    def list_branches(self, token: str) -> list[str]:
        branches: list[str] = []
        page = 1
        while True:
            payload = self._call(
                token,
                "GET",
                f"{self._repository_path()}/branches?per_page=100&page={page}",
            )
            if not isinstance(payload, list):
                raise GitHubTransportError("GitHub returned invalid branch data")
            names = [_required_string(item, "name") for item in payload]
            branches.extend(names)
            if len(names) < 100:
                return branches
            page += 1

    def create_branch(self, token: str, name: str, from_sha: str) -> None:
        self._call(
            token,
            "POST",
            f"{self._repository_path()}/git/refs",
            {"ref": f"refs/heads/{name}", "sha": from_sha},
        )

    def get_tree(self, token: str, branch: str) -> tuple[TreeEntry, ...]:
        payload = self._call(
            token,
            "GET",
            f"{self._repository_path()}/git/trees/{quote(branch, safe='')}?recursive=1",
        )
        if not isinstance(payload, Mapping):
            raise GitHubTransportError("GitHub returned invalid tree data")
        if payload.get("truncated") is not False:
            raise GitHubTransportError("GitHub returned a truncated tree")
        tree = payload.get("tree")
        if not isinstance(tree, list):
            raise GitHubTransportError("GitHub returned invalid tree data")
        return tuple(
            TreeEntry(
                path=_required_string(entry, "path"),
                type=_required_string(entry, "type"),
                sha=_required_string(entry, "sha"),
            )
            for entry in tree
        )

    def get_blob(self, token: str, sha: str) -> bytes:
        payload = self._call(token, "GET", f"{self._repository_path()}/git/blobs/{quote(sha, safe='')}")
        if _required_string(payload, "encoding") != "base64":
            raise GitHubTransportError("GitHub returned unsupported blob encoding")
        try:
            content = "".join(_required_string(payload, "content").split())
            return base64.b64decode(content, validate=True)
        except ValueError as error:
            raise GitHubTransportError("GitHub returned invalid blob data") from error

    def put_file(
        self,
        token: str,
        path: str,
        branch: str,
        content: bytes,
        message: str,
        sha: str | None,
    ) -> str:
        payload: dict[str, str] = {
            "message": message,
            "content": base64.b64encode(content).decode("ascii"),
            "branch": branch,
        }
        if sha is not None:
            payload["sha"] = sha
        response = self._call(
            token,
            "PUT",
            f"{self._repository_path()}/contents/{quote(path, safe='/')}",
            payload,
        )
        return _required_string(_required_object(response, "commit"), "sha")

    def commit_files(
        self,
        token: str,
        branch: str,
        expected_head_sha: str,
        changes: Mapping[str, bytes | None],
        message: str,
    ) -> str:
        """Atomically apply file writes and removals in one Git commit."""
        if self.get_branch_head_sha(token, branch) != expected_head_sha:
            raise GitHubConflictError("branch changed; reload and try again")
        commit = self._call(
            token,
            "GET",
            f"{self._repository_path()}/git/commits/{quote(expected_head_sha, safe='')}",
        )
        base_tree_sha = _required_string(_required_object(commit, "tree"), "sha")
        tree: list[dict[str, object]] = []
        for path, content in changes.items():
            entry: dict[str, object] = {
                "path": path,
                "mode": "100644",
                "type": "blob",
            }
            if content is None:
                entry["sha"] = None
            else:
                blob = self._call(
                    token,
                    "POST",
                    f"{self._repository_path()}/git/blobs",
                    {
                        "content": base64.b64encode(content).decode("ascii"),
                        "encoding": "base64",
                    },
                )
                entry["sha"] = _required_string(blob, "sha")
            tree.append(entry)
        created_tree = self._call(
            token,
            "POST",
            f"{self._repository_path()}/git/trees",
            {"base_tree": base_tree_sha, "tree": tree},
        )
        created_commit = self._call(
            token,
            "POST",
            f"{self._repository_path()}/git/commits",
            {
                "message": message,
                "tree": _required_string(created_tree, "sha"),
                "parents": [expected_head_sha],
            },
        )
        commit_sha = _required_string(created_commit, "sha")
        self._call(
            token,
            "PATCH",
            f"{self._repository_path()}/git/refs/heads/{quote(branch, safe='')}",
            {"sha": commit_sha, "force": False},
            conflict_on_422=True,
        )
        return commit_sha

    def create_pull_request(
        self, token: str, title: str, head: str, base: str, body: str
    ) -> str:
        payload = self._call(
            token,
            "POST",
            f"{self._repository_path()}/pulls",
            {"title": title, "head": head, "base": base, "body": body},
        )
        return _required_string(payload, "html_url")

    def get_authenticated_user(self, token: str) -> str:
        return _required_string(self._call(token, "GET", "/user"), "login")

    def _repository_path(self) -> str:
        return f"/repos/{self._owner}/{self._repo}"

    def _call(
        self,
        token: str,
        method: str,
        path: str,
        payload: Mapping[str, object] | None = None,
        *,
        conflict_on_422: bool = False,
    ) -> Mapping[str, Any] | list[Any]:
        data = (
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
            if payload is not None
            else None
        )
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=data,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            raise _github_http_error(error, token, conflict_on_422=conflict_on_422) from error
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as error:
            raise GitHubTransportError("Unable to reach GitHub") from error
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GitHubTransportError("GitHub returned malformed JSON") from error
        if not isinstance(decoded, (dict, list)):
            raise GitHubTransportError("GitHub returned invalid JSON data")
        return decoded


def _required_object(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GitHubTransportError("GitHub returned invalid response data")
    nested = value.get(field)
    if not isinstance(nested, Mapping):
        raise GitHubTransportError("GitHub returned invalid response data")
    return nested


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, Mapping) or not isinstance(value.get(field), str):
        raise GitHubTransportError("GitHub returned invalid response data")
    return value[field]


def _github_http_error(
    error: urllib.error.HTTPError,
    token: str,
    *,
    conflict_on_422: bool = False,
) -> GitHubError:
    message = _github_error_message(error, token)
    if error.code == 404:
        return GitHubNotFoundError(message)
    if error.code in {409, 412} or (error.code == 422 and conflict_on_422):
        return GitHubConflictError(message)
    if error.code == 401:
        return GitHubAuthError(message)
    if error.code == 403:
        if error.headers.get("X-RateLimit-Remaining") == "0":
            return GitHubRateLimitError(message)
        return GitHubForbiddenError(message)
    return GitHubTransportError(message)


def _github_error_message(error: urllib.error.HTTPError, token: str) -> str:
    try:
        payload = json.loads(error.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, Mapping) and isinstance(payload.get("message"), str):
        message = payload["message"]
        return message.replace(token, "[REDACTED]") if token else message
    return f"GitHub request failed with HTTP {error.code}"
