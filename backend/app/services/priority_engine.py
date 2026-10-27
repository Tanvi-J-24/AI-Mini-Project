"""Rule-based rescue priority engine (forward chaining).

This is NOT a machine-learning model. Facts about an incident are placed in a
working memory; rules whose conditions match are fired repeatedly until no rule
changes the memory (a fixed point). Rules only ever RAISE the priority level,
so the loop always terminates.

Working-memory facts:
    severity        'critical' | 'high' | 'medium' | 'low'
    people_affected int
    resolved        bool
    route_available bool   (can any rescue station currently reach the incident?)
    level           int    derived priority level (0 none, 1 Low ... 4 Critical)
    needs_alt_access bool  derived flag

Rules (see RULES below):
    R0  resolved incident              -> removed from active queue (stops chaining)
    R1  severity == critical           -> level >= Critical
    R2  severity == high               -> level >= High
    R3  severity == medium             -> level >= Medium
    R4  severity == low                -> level >= Low
    R5  level == High and people >= 25 -> level = Critical      (chained on R2)
    R6  level == Medium and people>=15 -> level = High          (chained on R3)
    R7  route unavailable              -> flag for alternative access planning
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

LEVELS = {0: "None", 1: "Low", 2: "Medium", 3: "High", 4: "Critical"}
SEVERITY_LEVEL = {"low": 1, "medium": 2, "high": 3, "critical": 4}

Facts = dict[str, Any]


@dataclass(frozen=True)
class Rule:
    id: str
    description: str
    condition: Callable[[Facts], bool]
    action: Callable[[Facts], bool]  # returns True if working memory changed


def _raise_to(level: int) -> Callable[[Facts], bool]:
    def act(f: Facts) -> bool:
        if f["level"] < level:
            f["level"] = level
            return True
        return False
    return act


def _flag_alt_access(f: Facts) -> bool:
    if not f["needs_alt_access"]:
        f["needs_alt_access"] = True
        return True
    return False


RULES: list[Rule] = [
    Rule("R1", "Critical severity -> Critical priority",
         lambda f: f["severity"] == "critical", _raise_to(4)),
    Rule("R2", "High severity -> High priority",
         lambda f: f["severity"] == "high", _raise_to(3)),
    Rule("R3", "Medium severity -> Medium priority",
         lambda f: f["severity"] == "medium", _raise_to(2)),
    Rule("R4", "Low severity -> Low priority",
         lambda f: f["severity"] == "low", _raise_to(1)),
    Rule("R5", "High priority and >= 25 people affected -> escalate to Critical",
         lambda f: f["level"] == 3 and f["people_affected"] >= 25, _raise_to(4)),
    Rule("R6", "Medium priority and >= 15 people affected -> escalate to High",
         lambda f: f["level"] == 2 and f["people_affected"] >= 15, _raise_to(3)),
    Rule("R7", "No route from any station -> flag for alternative access planning",
         lambda f: not f["route_available"], _flag_alt_access),
]

RESOLVED_RULE = ("R0", "Resolved incident -> removed from the active queue")


def evaluate(severity: str, people_affected: int, resolved: bool, route_available: bool) -> dict:
    """Run forward chaining for one incident and return priority + explanation."""
    if resolved:
        return {
            "priority": "Resolved", "level": 0, "score": 0, "in_queue": False,
            "needs_alt_access": False,
            "rules_fired": [{"id": RESOLVED_RULE[0], "description": RESOLVED_RULE[1]}],
            "reason": RESOLVED_RULE[1],
        }

    facts: Facts = {
        "severity": severity, "people_affected": people_affected, "resolved": False,
        "route_available": route_available, "level": 0, "needs_alt_access": False,
    }
    fired: list[Rule] = []
    changed = True
    guard = 0
    while changed and guard < 50:  # guard is a safety net; rules are monotonic
        guard += 1
        changed = False
        for rule in RULES:
            if rule.condition(facts) and rule.action(facts):
                fired.append(rule)
                changed = True

    level = facts["level"]
    level_rules = [r for r in fired if r.id in {"R1", "R2", "R3", "R4", "R5", "R6"}]
    reason = level_rules[-1].description if level_rules else "No rule matched"
    if facts["needs_alt_access"]:
        reason += " | " + RULES[-1].description
    return {
        "priority": LEVELS[level], "level": level,
        "score": level * 100 + min(max(people_affected, 0), 99),
        "in_queue": True, "needs_alt_access": facts["needs_alt_access"],
        "rules_fired": [{"id": r.id, "description": r.description} for r in fired],
        "reason": reason,
    }
