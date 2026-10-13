from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class Violation:
    category: str
    message: str
    severity: Severity = Severity.BLOCK
    rule_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.category.strip():
            raise ValueError("Violation category must not be empty")
        if not self.message.strip():
            raise ValueError("Violation message must not be empty")


@dataclass(frozen=True, slots=True)
class GuardrailResult:
    violations: tuple[Violation, ...] = ()
    sanitized_text: str | None = None

    @property
    def allowed(self) -> bool:
        return not any(violation.severity == Severity.BLOCK for violation in self.violations)

    @classmethod
    def allow(cls, *, sanitized_text: str | None = None) -> "GuardrailResult":
        return cls(sanitized_text=sanitized_text)

    @classmethod
    def reject(cls, *violations: Violation, sanitized_text: str | None = None) -> "GuardrailResult":
        if not any(violation.severity == Severity.BLOCK for violation in violations):
            raise ValueError("A rejected result requires a blocking violation")
        return cls(violations=tuple(violations), sanitized_text=sanitized_text)
