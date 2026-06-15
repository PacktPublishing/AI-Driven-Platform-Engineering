from pathlib import Path

from .settings import settings
from .skills import skills_system_prompt_section


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_system_prompt() -> str:
    """Compose the system prompt from identity files plus skill metadata.

    SOUL.md, IDENTITY.md, USER.md are mounted read-only from a ConfigMap and
    version-controlled in the components repo. MEMORY.md lives on a PVC and
    is appended to by save_to_memory(). Skills are folders under SKILLS_DIR;
    we expose their metadata at startup and let the model pull the full body
    on demand via consult_skill().
    """
    soul = _read(settings.identity_dir / "SOUL.md")
    identity = _read(settings.identity_dir / "IDENTITY.md")
    user = _read(settings.identity_dir / "USER.md")
    memory = _read(settings.memory_file)
    skills = skills_system_prompt_section()

    sections = []
    if soul:
        sections.append(f"# Who you are\n\n{soul}")
    if identity:
        sections.append(f"# What you can do\n\n{identity}")
    if user:
        sections.append(f"# About the user you serve\n\n{user}")
    if memory:
        sections.append(f"# What you have committed to long-term memory\n\n{memory}")
    if skills:
        sections.append(skills)

    return "\n\n---\n\n".join(sections)


def append_memory(fact: str) -> None:
    """Append a fact to MEMORY.md. Called by the save_to_memory tool."""
    settings.memory_file.parent.mkdir(parents=True, exist_ok=True)
    with settings.memory_file.open("a", encoding="utf-8") as f:
        f.write(f"- {fact.strip()}\n")
