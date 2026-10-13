from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .models import GuardrailResult, Violation


class Guardrail(Protocol):
    async def validate(self, text: str) -> GuardrailResult: ...


class GuardrailPipeline:
    def __init__(self, guardrails: Sequence[Guardrail], *, stop_on_rejection: bool = True) -> None:
        self._guardrails = tuple(guardrails)
        self._stop_on_rejection = stop_on_rejection

    async def validate(self, text: str) -> GuardrailResult:
        current_text = text
        violations: list[Violation] = []
        for guardrail in self._guardrails:
            result = await guardrail.validate(current_text)
            violations.extend(result.violations)
            if result.sanitized_text is not None:
                current_text = result.sanitized_text
            if not result.allowed and self._stop_on_rejection:
                return GuardrailResult(
                    violations=tuple(violations),
                    sanitized_text=current_text if current_text != text else None,
                )
        return GuardrailResult(
            violations=tuple(violations),
            sanitized_text=current_text if current_text != text else None,
        )
