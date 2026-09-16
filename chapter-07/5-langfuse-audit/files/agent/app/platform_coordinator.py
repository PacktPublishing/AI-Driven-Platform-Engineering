"""Create the Platform Coordinator for a request, restoring its conversation session.

Coordinator tools: Backstage catalog search, TechDocs search, memory, and the
three specialist handoff tools supplied by ``coordinator_tools.py``.
"""

from strands import Agent, tool
from strands.models import BedrockModel
from strands.session.file_session_manager import FileSessionManager

from .audit import AuditHook, AuditLog
from .hooks_langfuse import LangfuseStrandsHook
from .hooks import AlwaysPRHook
from .identity import append_memory, load_system_prompt
from .mcp_clients import gitops_tools, cluster_tools
from .coordinator_tools import delegation_tools, BudgetHook
from .catalog import search_catalog, search_documentation
from .settings import settings
from .skills import discover_skills, load_skill_body


_audit_log = AuditLog(settings.audit_log)

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


@tool
def consult_skill(name: str) -> str:
    """Load the full body of a skill by name. Use this when the user's intent
    matches a skill's description in the system prompt. Returns the SKILL.md
    contents (frontmatter + procedure). Follow the procedure step by step."""
    body = load_skill_body(name)
    if body is None:
        available = ", ".join(s.name for s in discover_skills()) or "(none)"
        return f"Skill {name!r} not found. Available skills: {available}"
    return body


def create_coordinator(session_id: str = "default") -> Agent:
    settings.session_dir.mkdir(parents=True, exist_ok=True)
    session_manager = FileSessionManager(
        session_id=session_id,
        storage_dir=str(settings.session_dir),
    )
    budget = {'remaining': 24, 'limit': 24}
    def hooks_for(actor):
        return [AlwaysPRHook(), AuditHook(_audit_log, actor), LangfuseStrandsHook(actor)]
    specialist_tools = delegation_tools(
        _make_model, cluster_tools(), gitops_tools(), consult_skill, hooks_for, budget
    )
    coordinator_tools = [
        save_to_memory,
        search_catalog,
        search_documentation,
        *specialist_tools,
    ]
    return Agent(
        model=_make_model(),
        system_prompt=load_system_prompt() + '\nYou are the Platform Coordinator. '
            'For live health delegate to diagnose_application; for Git questions use review_configuration; '
            'only when the user requests a repair delegate to propose_change with evidence. '
            'Ask which application if unclear. Never invent evidence or PR URLs. '
            'Catalog and documentation search remain available. No direct cluster mutation or PR merge. '
            'After human merge, diagnose again only on a follow-up request.',
        session_manager=session_manager,
        tools=coordinator_tools,
        hooks=[BudgetHook(budget), *hooks_for('coordinator')],
    )
