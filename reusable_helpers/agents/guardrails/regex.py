from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern

from .models import GuardrailResult, Severity, Violation


@dataclass(frozen=True, slots=True)
class RegexRule:
    id: str
    category: str
    pattern: str | Pattern[str]
    message: str
    severity: Severity = Severity.BLOCK
    flags: int = re.IGNORECASE

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Regex rule id must not be empty")

    def compile(self) -> Pattern[str]:
        if isinstance(self.pattern, re.Pattern):
            return self.pattern
        return re.compile(self.pattern, self.flags)


class RegexGuardrail:
    def __init__(
        self,
        rules: tuple[RegexRule, ...] | list[RegexRule],
        *,
        collect_all: bool = False,
    ) -> None:
        self._rules = tuple((rule, rule.compile()) for rule in rules)
        self._collect_all = collect_all

    async def validate(self, text: str) -> GuardrailResult:
        violations: list[Violation] = []
        for rule, pattern in self._rules:
            match = pattern.search(text)
            if match is None:
                continue
            violations.append(
                Violation(
                    rule_id=rule.id,
                    category=rule.category,
                    message=rule.message,
                    severity=rule.severity,
                    metadata={"match_start": match.start(), "match_end": match.end()},
                )
            )
            if rule.severity == Severity.BLOCK and not self._collect_all:
                break
        return GuardrailResult(violations=tuple(violations))
