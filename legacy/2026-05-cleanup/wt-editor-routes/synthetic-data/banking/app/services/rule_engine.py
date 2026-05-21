import yaml
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Rule:
    name: str
    condition: str
    action: str
    priority: int = 0
    params: Dict[str, Any] = None

class BankingRuleEngine:
    def __init__(self, rules_path: str = "rules/banking_rules.yaml"):
        with open(rules_path) as f:
            raw_rules = yaml.safe_load(f)
        self.rules = [Rule(**r) for r in raw_rules.get("rules", [])]
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def apply(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        enriched = constraints.copy()
        age = 2026 - int(constraints.get("birth_year", 1990))

        for rule in self.rules:
            if self._evaluate_condition(rule.condition, enriched, age):
                enriched = self._execute_action(rule.action, enriched, rule.params)

        return enriched

    def _evaluate_condition(self, condition: str, ctx: Dict[str, Any], age: int) -> bool:
        local_vars = {**ctx, "age": age}
        try:
            return eval(condition, {"__builtins__": {}}, local_vars)
        except Exception as e:
            return False

    def _execute_action(self, action: str, ctx: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "set_salary_range":
            ctx["salary_range"] = params
        elif action == "set_account_type":
            ctx["account_type"] = params.get("type")
        elif action == "add_eligible_products":
            ctx["eligible_products"] = params.get("products", [])
        elif action == "set_account_mix":
            ctx["account_mix"] = params.get("mix", ["CHECKING"])
        elif action == "set_credit_score_range":
            ctx["credit_score_range"] = params
        elif action == "add_eligible_card":
            if "eligible_cards" not in ctx:
                ctx["eligible_cards"] = []
            ctx["eligible_cards"].append(params)
        return ctx
