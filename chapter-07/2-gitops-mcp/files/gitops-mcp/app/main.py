import logging

from mcp.server.fastmcp import FastMCP
from pythonjsonlogger import jsonlogger

from .git_ops import open_pr as _open_pr
from .git_ops import read_file as _read_file
from .settings import settings

logger = logging.getLogger("gitops-mcp")
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

mcp = FastMCP("gitops-mcp", host="0.0.0.0", port=settings.port)


@mcp.tool()
def read_file(path: str) -> dict:
    """Read a file from the GitOps repository (Backstage components repo).

    Use this to inspect the current state of any manifest before proposing
    a change. Returns {path, content, sha} where content is the decoded UTF-8
    text of the file on the default branch.

    Args:
        path: Repo-relative path, e.g. 'my-first-app/k8s/deployment.yaml'.
    """
    logger.info("read_file", extra={"path": path})
    return _read_file(path)


@mcp.tool()
def open_pull_request(
    branch: str,
    file_path: str,
    content: str,
    commit_message: str,
    title: str,
    body: str,
) -> dict:
    """Open a pull request that modifies a single file in the GitOps repo.

    This is the ONLY mutation tool. It creates the branch from the default
    branch (if it does not already exist), commits the edited file content,
    and opens a pull request. Returns {url, number}.

    Args:
        branch: New branch name. Convention: 'agent/<short-summary>'.
        file_path: Repo-relative path of the file to change.
        content: Full new file content (the edit is whole-file replace).
        commit_message: Commit message for the change.
        title: PR title. Convention: '[agent] <verb> <resource> in <namespace>'.
        body: PR body. Include rationale and a link back to the conversation
              that produced the change when one is available.
    """
    logger.info(
        "open_pull_request",
        extra={"branch": branch, "file_path": file_path, "title": title},
    )
    return _open_pr(branch, file_path, content, commit_message, title, body)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
