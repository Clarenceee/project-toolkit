"""Evaluate model output against a caller-supplied rubric."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol


class EvaluationError(RuntimeError):
    """Raised when a judge response cannot be used as a score."""


class TextModelClient(Protocol):
    async def complete(self, *, instructions: str, input_text: str) -> str: ...


@dataclass(frozen=True, slots=True)
class JudgeResult:
    score: float
    explanation: str
    raw_response: str

    def __post_init__(self) -> None:
        if not self.explanation.strip():
            raise ValueError("Judge explanation must not be empty")


class LLMJudge:
    def __init__(
        self,
        client: TextModelClient,
        *,
        minimum_score: float = 1,
        maximum_score: float = 5,
        attempts: int = 1,
    ) -> None:
        if minimum_score >= maximum_score:
            raise ValueError("minimum_score must be below maximum_score")
        if attempts < 1:
            raise ValueError("attempts must be positive")
        self._client = client
        self._minimum = minimum_score
        self._maximum = maximum_score
        self._attempts = attempts

    async def evaluate(self, *, query: str, response: str, rubric: str) -> JudgeResult:
        prompt = (
            f"Query:\n{query}\n\nResponse:\n{response}\n\nRubric:\n{rubric}\n\n"
            "Return one JSON object with numeric field 'score' and string field 'explanation'."
        )
        last_error: Exception | None = None
        for _ in range(self._attempts):
            raw = await self._client.complete(
                instructions=(
                    "You are an evaluator. Apply the rubric consistently "
                    "and return only valid JSON."
                ),
                input_text=prompt,
            )
            try:
                return self._parse(raw)
            except (EvaluationError, TypeError, ValueError) as exc:
                last_error = exc
        raise EvaluationError(f"Judge failed after {self._attempts} attempt(s): {last_error}")

    def _parse(self, raw: str) -> JudgeResult:
        try:
            payload = json.loads(raw.strip())
        except json.JSONDecodeError as exc:
            raise EvaluationError("Judge returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise EvaluationError("Judge result must be a JSON object")
        score = float(payload["score"])
        explanation = payload["explanation"]
        if not self._minimum <= score <= self._maximum:
            raise EvaluationError(f"Score {score} is outside {self._minimum}..{self._maximum}")
        if not isinstance(explanation, str) or not explanation.strip():
            raise EvaluationError("Judge explanation must be non-empty text")
        return JudgeResult(score=score, explanation=explanation.strip(), raw_response=raw)


class OpenAIResponsesTextClient:
    """Adapter for an injected AsyncOpenAI-compatible client."""

    def __init__(self, client: Any, *, model: str, service_tier: str | None = None) -> None:
        self._client = client
        self._model = model
        self._service_tier = service_tier

    async def complete(self, *, instructions: str, input_text: str) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "instructions": instructions,
            "input": input_text,
        }
        if self._service_tier is not None:
            kwargs["service_tier"] = self._service_tier
        response = await self._client.responses.create(**kwargs)
        return response.output_text or ""
