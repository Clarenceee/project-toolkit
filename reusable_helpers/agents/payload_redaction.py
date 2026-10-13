from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Pattern


@dataclass(frozen=True, slots=True)
class RegexRedactionRule:
    pattern: str | Pattern[str]
    replacement: str = "[REDACTED]"
    flags: int = 0

    def compile(self) -> Pattern[str]:
        if isinstance(self.pattern, re.Pattern):
            return self.pattern
        return re.compile(self.pattern, self.flags)


@dataclass(frozen=True, slots=True)
class RedactionResult:
    value: Any
    replacements: int

    @property
    def changed(self) -> bool:
        return self.replacements > 0


class PayloadRedactor:
    def __init__(
        self,
        *,
        sensitive_fields: Sequence[str] = (),
        text_rules: Sequence[RegexRedactionRule] = (),
        field_replacement: Any = "[REDACTED]",
        case_sensitive_fields: bool = False,
    ) -> None:
        normalize = (
            (lambda value: value) if case_sensitive_fields else (lambda value: value.casefold())
        )
        self._normalize_field = normalize
        self._sensitive_fields = {normalize(field) for field in sensitive_fields}
        self._rules = tuple((rule.compile(), rule.replacement) for rule in text_rules)
        self._field_replacement = field_replacement

    def redact(self, value: Any) -> RedactionResult:
        redacted, count = self._redact(value)
        return RedactionResult(value=redacted, replacements=count)

    def _redact(self, value: Any) -> tuple[Any, int]:
        if isinstance(value, str):
            return self._redact_text(value)
        if isinstance(value, Mapping):
            output: dict[Any, Any] = {}
            replacements = 0
            for key, item in value.items():
                if self._normalize_field(str(key)) in self._sensitive_fields:
                    output[key] = self._field_replacement
                    replacements += 1
                else:
                    output[key], count = self._redact(item)
                    replacements += count
            return output, replacements
        if isinstance(value, tuple):
            items = [self._redact(item) for item in value]
            return tuple(item for item, _ in items), sum(count for _, count in items)
        if isinstance(value, list):
            items = [self._redact(item) for item in value]
            return [item for item, _ in items], sum(count for _, count in items)
        return value, 0

    def _redact_text(self, text: str) -> tuple[str, int]:
        output = text
        replacements = 0
        for pattern, replacement in self._rules:
            output, count = pattern.subn(replacement, output)
            replacements += count
        return output, replacements
