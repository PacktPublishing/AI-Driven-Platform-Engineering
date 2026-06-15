import os
from pathlib import Path


class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "bedrock")

    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    aws_region: str = os.getenv("AWS_REGION", "us-west-2")

    anthropic_model_id: str = os.getenv("ANTHROPIC_MODEL_ID", "claude-sonnet-4-5")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")

    identity_dir: Path = Path(os.getenv("IDENTITY_DIR", "/state/identity"))
    session_dir: Path = Path(os.getenv("SESSION_DIR", "/state/sessions"))
    memory_file: Path = Path(os.getenv("MEMORY_FILE", "/state/memory/MEMORY.md"))
    skills_dir: Path = Path(os.getenv("SKILLS_DIR", "/state/skills"))

    mcp_gitops_url: str | None = os.getenv("MCP_GITOPS_URL")
    backstage_url: str = os.getenv("BACKSTAGE_URL", "http://host.docker.internal:7007")


settings = Settings()
