from pathlib import Path

from .settings import settings


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_system_prompt() -> str:
    """Compose the system prompt from the identity files.

    SOUL.md, IDENTITY.md, USER.md are mounted read-only from a ConfigMap
    and version-controlled in the components repo. MEMORY.md lives on a
    PVC and is appended to by save_to_memory().
    """
    soul = _read(settings.identity_dir / "SOUL.md")
    identity = _read(settings.identity_dir / "IDENTITY.md")
    user = _read(settings.identity_dir / "USER.md")
    memory = _read(settings.memory_file)

    sections = []
    if soul:
        sections.append(f"# Who you are\n\n{soul}")
    if identity:
        sections.append(f"# What you can do\n\n{identity}")
    if user:
        sections.append(f"# About the user you serve\n\n{user}")
    if memory:
        sections.append(f"# What you have committed to long-term memory\n\n{memory}")

    return "\n\n---\n\n".join(sections)


def append_memory(fact: str) -> None:
    """Append a fact to MEMORY.md. Called by the save_to_memory tool."""
    settings.memory_file.parent.mkdir(parents=True, exist_ok=True)
    with settings.memory_file.open("a", encoding="utf-8") as f:
        f.write(f"- {fact.strip()}\n")
