import os


class Settings:
    github_token: str = os.environ["GITHUB_TOKEN"]
    repo_owner: str = os.environ.get("GITOPS_REPO_OWNER", "lusoal")
    repo_name: str = os.environ.get("GITOPS_REPO_NAME", "backstage-components")
    default_branch: str = os.environ.get("GITOPS_DEFAULT_BRANCH", "main")
    port: int = int(os.environ.get("PORT", "8080"))


settings = Settings()
