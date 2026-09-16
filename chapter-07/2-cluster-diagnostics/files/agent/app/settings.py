import os


class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "bedrock")

    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    aws_region: str = os.getenv("AWS_REGION", "us-west-2")

    anthropic_model_id: str = os.getenv("ANTHROPIC_MODEL_ID", "claude-sonnet-4-5")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")



settings = Settings()
