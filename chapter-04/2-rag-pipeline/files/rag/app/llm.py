"""Generation: turn retrieved context + a question into a grounded answer.

Supports Amazon Bedrock (Claude) and the Anthropic API directly — the same
two-provider pattern Chapter 6 uses. If neither is configured, generation is
disabled and the API returns retrieval-only results.

The system prompt is the important part: the model is told to answer ONLY from
the supplied context and to say so when the answer isn't there. That's what
makes this *grounded* — the difference between RAG and just asking a chatbot.
"""
from __future__ import annotations

import os

from .settings import Settings
from .store import Retrieved

SYSTEM_PROMPT = """You are a platform-engineering assistant. Answer the user's \
question using ONLY the provided context, which comes from the organization's \
runbooks, postmortems, and platform blueprints.

Rules:
- Ground every claim in the context. Do not use outside knowledge.
- If the context does not contain the answer, say so plainly.
- Cite the source files you used by their path (e.g. runbooks/crashloopbackoff.md).
- Be concise and practical — this is for an engineer mid-task."""


def _format_context(contexts: list[Retrieved]) -> str:
    blocks = []
    for c in contexts:
        blocks.append(f"[source: {c.source} | type: {c.doc_type} | owner: {c.owner}]\n{c.content}")
    return "\n\n---\n\n".join(blocks)


def _user_message(question: str, contexts: list[Retrieved]) -> str:
    return f"Context:\n\n{_format_context(contexts)}\n\n---\n\nQuestion: {question}"


def _resolve_provider(settings: Settings) -> str:
    if settings.llm_provider != "auto":
        return settings.llm_provider
    # Auto-detect: prefer Bedrock if AWS creds look present, else Anthropic.
    if os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE") or os.getenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"):
        return "bedrock"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "none"


def _generate_bedrock(settings: Settings, question: str, contexts: list[Retrieved]) -> str:
    import boto3

    client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    resp = client.converse(
        modelId=settings.bedrock_model_id,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": _user_message(question, contexts)}]}],
        inferenceConfig={"maxTokens": settings.max_tokens, "temperature": 0.0},
    )
    return resp["output"]["message"]["content"][0]["text"]


def _generate_anthropic(settings: Settings, question: str, contexts: list[Retrieved]) -> str:
    import anthropic

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=settings.max_tokens,
        temperature=0.0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _user_message(question, contexts)}],
    )
    return "".join(block.text for block in msg.content if block.type == "text")


def generate(settings: Settings, question: str, contexts: list[Retrieved]) -> str | None:
    """Return a grounded answer, or None if generation is disabled/unavailable."""
    provider = _resolve_provider(settings)
    if provider == "none" or not contexts:
        return None
    if provider == "bedrock":
        return _generate_bedrock(settings, question, contexts)
    if provider == "anthropic":
        return _generate_anthropic(settings, question, contexts)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def active_provider(settings: Settings) -> str:
    return _resolve_provider(settings)
