import logging
import re

from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry

logger = logging.getLogger("agent.hook")

_PR_TITLE = re.compile(r"^\[agent\] ")
_MIN_BODY = 20


class AlwaysPRHook(HookProvider):
    """Code-level governance: enforce that every PR the agent opens follows
    the conventional title prefix and contains a non-trivial rationale.

    The agent's system prompt also says these things, but a prompt is a hint
    the model can ignore. A hook is code that runs on every tool call,
    regardless of what the prompt says.
    """

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self._before_tool)

    def _before_tool(self, event: BeforeToolCallEvent) -> None:
        if event.selected_tool is None:
            return
        name = event.selected_tool.tool_name
        params = event.tool_use.get("input", {}) or {}

        logger.info(
            "hook.before_tool",
            extra={"tool": name, "tool_args": list(params.keys())},
        )

        if name != "open_pull_request":
            return

        title = params.get("title", "")
        body = params.get("body", "")

        if not _PR_TITLE.match(title):
            event.cancel_tool = (
                f"Hook rejected open_pull_request: title must start with '[agent] '. "
                f"Got: {title!r}. Re-call with a corrected title."
            )
            logger.warning("hook.reject", extra={"reason": "bad_title", "title": title})
            return

        if len(body.strip()) < _MIN_BODY:
            event.cancel_tool = (
                f"Hook rejected open_pull_request: body must include a rationale of at least "
                f"{_MIN_BODY} characters. Explain the symptom, the change, and why."
            )
            logger.warning("hook.reject", extra={"reason": "short_body", "body_len": len(body)})
            return
