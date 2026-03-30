from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


RULES_FILE = Path(__file__).resolve().parent / "compliance_rules.json"


@lru_cache(maxsize=1)
def load_compliance_rules() -> dict[str, Any]:
    payload = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "rules" not in payload:
        raise ValueError("Arquivo compliance_rules.json inválido")
    return payload


def get_rule(rule_code: str) -> dict[str, Any]:
    rules = load_compliance_rules().get("rules", {})
    selected = rules.get(rule_code)
    if not isinstance(selected, dict):
        raise KeyError(f"Regra não encontrada: {rule_code}")
    return selected


def get_rule_param(rule_code: str, path: str, default: Any = None) -> Any:
    value: Any = get_rule(rule_code)
    for key in path.split("."):
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return value if value is not None else default
