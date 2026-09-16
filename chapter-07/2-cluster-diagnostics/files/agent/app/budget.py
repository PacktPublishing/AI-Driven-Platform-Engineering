from strands.hooks import HookProvider, BeforeToolCallEvent


class BudgetHook(HookProvider):
    def __init__(self, budget):
        self.budget = budget

    def register_hooks(self, registry):
        registry.add_callback(BeforeToolCallEvent, self.before)

    def before(self, event):
        self.budget['remaining'] -= 1
        if self.budget['remaining'] < 0:
            raise RuntimeError('request_tool_budget_exhausted')


