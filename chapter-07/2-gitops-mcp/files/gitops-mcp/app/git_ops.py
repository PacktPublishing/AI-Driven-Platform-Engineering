import base64

import httpx

from .settings import settings

GH_API = "https://api.github.com"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo_path(suffix: str) -> str:
    return f"{GH_API}/repos/{settings.repo_owner}/{settings.repo_name}{suffix}"


def read_file(path: str) -> dict:
    """Return the current content of `path` on the default branch."""
    r = httpx.get(
        _repo_path(f"/contents/{path}"),
        headers=_headers(),
        params={"ref": settings.default_branch},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "path": path,
        "content": base64.b64decode(data["content"]).decode("utf-8"),
        "sha": data["sha"],
    }


def open_pr(
    branch: str,
    file_path: str,
    content: str,
    commit_message: str,
    title: str,
    body: str,
) -> dict:
    """Create `branch` from default, commit a single-file edit on it, and open a PR.

    Returns {"url": pr_html_url, "number": pr_number}.
    """
    base_branch = settings.default_branch

    current_sha = read_file(file_path)["sha"]

    r = httpx.get(_repo_path(f"/branches/{base_branch}"), headers=_headers(), timeout=30)
    r.raise_for_status()
    base_sha = r.json()["commit"]["sha"]

    r = httpx.post(
        _repo_path("/git/refs"),
        headers=_headers(),
        json={"ref": f"refs/heads/{branch}", "sha": base_sha},
        timeout=30,
    )
    if r.status_code not in (201, 422):
        r.raise_for_status()

    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    r = httpx.put(
        _repo_path(f"/contents/{file_path}"),
        headers=_headers(),
        json={
            "message": commit_message,
            "content": encoded,
            "sha": current_sha,
            "branch": branch,
        },
        timeout=30,
    )
    r.raise_for_status()

    r = httpx.post(
        _repo_path("/pulls"),
        headers=_headers(),
        json={"title": title, "head": branch, "base": base_branch, "body": body},
        timeout=30,
    )
    r.raise_for_status()
    return {"url": r.json()["html_url"], "number": r.json()["number"]}
