import base64
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
    audit_log: Path = Path(os.getenv("AUDIT_LOG", "/state/audit/AUDIT.log"))

    mcp_gitops_url: str | None = os.getenv("MCP_GITOPS_URL")
    backstage_url: str = os.getenv("BACKSTAGE_URL", "http://host.docker.internal:7007")

    agent_id: str = os.getenv("AGENT_ID", "platform-ops")

    # Langfuse via OpenTelemetry. Set LANGFUSE_HOST + LANGFUSE_PUBLIC_KEY +
    # LANGFUSE_SECRET_KEY in env (typically from a Secret) to enable.
    langfuse_host: str | None = os.getenv("LANGFUSE_HOST")
    langfuse_public_key: str | None = os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = os.getenv("LANGFUSE_SECRET_KEY")

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_host and self.langfuse_public_key and self.langfuse_secret_key)

    @property
    def otlp_endpoint(self) -> str:
        # Langfuse exposes OTLP HTTP at /api/public/otel/v1/traces
        return f"{self.langfuse_host.rstrip('/')}/api/public/otel/v1/traces"

    @property
    def otlp_basic_auth_header(self) -> str:
        token = base64.b64encode(
            f"{self.langfuse_public_key}:{self.langfuse_secret_key}".encode()
        ).decode("ascii")
        return f"Basic {token}"


settings = Settings()
