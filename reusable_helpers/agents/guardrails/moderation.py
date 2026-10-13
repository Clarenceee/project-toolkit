from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from .models import GuardrailResult, Severity, Violation


@dataclass(frozen=True, slots=True)
class ModerationDecision:
    flagged: bool
    categories: Mapping[str, bool] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ModerationProvider(Protocol):
    async def check(self, text: str) -> ModerationDecision: ...


class ModerationGuardrail:
    def __init__(
        self,
        provider: ModerationProvider,
        *,
        category: str = "moderation",
        message: str = "Content was rejected by moderation",
        fail_closed: bool = True,
    ) -> None:
        self._provider = provider
        self._category = category
        self._message = message
        self._fail_closed = fail_closed

    async def validate(self, text: str) -> GuardrailResult:
        try:
            decision = await self._provider.check(text)
        except Exception as exc:
            if not self._fail_closed:
                return GuardrailResult.allow()
            return GuardrailResult.reject(
                Violation(
                    category="moderation_unavailable",
                    message="Moderation provider is unavailable",
                    severity=Severity.BLOCK,
                    metadata={"error_type": type(exc).__name__},
                )
            )
        if not decision.flagged:
            return GuardrailResult.allow()
        active_categories = tuple(name for name, active in decision.categories.items() if active)
        return GuardrailResult.reject(
            Violation(
                category=self._category,
                message=self._message,
                severity=Severity.BLOCK,
                metadata={**decision.metadata, "categories": active_categories},
            )
        )


class OpenAIModerationProvider:
    """Optional adapter for an AsyncOpenAI-compatible client."""

    def __init__(self, client: Any, *, model: str | None = None) -> None:
        self._client = client
        self._model = model

    async def check(self, text: str) -> ModerationDecision:
        kwargs: dict[str, Any] = {"input": text}
        if self._model is not None:
            kwargs["model"] = self._model
        response = await self._client.moderations.create(**kwargs)
        result = response.results[0]
        categories = (
            result.categories.model_dump()
            if hasattr(result.categories, "model_dump")
            else dict(result.categories)
        )
        scores = (
            result.category_scores.model_dump()
            if hasattr(result.category_scores, "model_dump")
            else dict(result.category_scores)
        )
        return ModerationDecision(
            flagged=bool(result.flagged),
            categories=categories,
            metadata={"category_scores": scores},
        )
