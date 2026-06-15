from strands import Agent, tool
from strands.models import BedrockModel
from strands.session.file_session_manager import FileSessionManager

from .identity import append_memory, load_system_prompt
from .settings import settings


def _make_model():
    if settings.llm_provider == "bedrock":
        return BedrockModel(
            model_id=settings.bedrock_model_id,
            region_name=settings.aws_region,
        )
    if settings.llm_provider == "anthropic":
        from strands.models.anthropic import AnthropicModel

        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for the anthropic provider")
        return AnthropicModel(
            model_id=settings.anthropic_model_id,
            api_key=settings.anthropic_api_key,
        )
    raise RuntimeError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")


@tool
def save_to_memory(fact: str) -> str:
    """Persist a fact to long-term memory (MEMORY.md). Use this only when a
    fact is important enough to survive across sessions — user preferences,
    durable platform invariants, decisions worth remembering. Routine
    conversational context does not belong here."""
    append_memory(fact)
    return f"Saved to MEMORY.md: {fact}"


def build_agent(session_id: str = "default") -> Agent:
    settings.session_dir.mkdir(parents=True, exist_ok=True)
    session_manager = FileSessionManager(
        session_id=session_id,
        storage_dir=str(settings.session_dir),
    )
    return Agent(
        model=_make_model(),
        system_prompt=load_system_prompt(),
        session_manager=session_manager,
        tools=[save_to_memory],
    )
