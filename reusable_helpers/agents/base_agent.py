from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from typing import Any, TypeAlias

from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessage
from pydantic_ai.result import StreamedRunResult

PreprocessorResult: TypeAlias = str | Awaitable[str]
PromptPreprocessor: TypeAlias = Callable[[str, Sequence[ModelMessage], Any], PreprocessorResult]


class BaseAgent:
    """Wrap Pydantic AI with consistent preprocessing, run, and stream behavior."""

    def __init__(
        self,
        agent: Agent[Any, Any],
        *,
        preprocessors: Sequence[PromptPreprocessor] = (),
    ) -> None:
        self._agent = agent
        self._preprocessors = tuple(preprocessors)

    async def _prepare_prompt(
        self, prompt: str, history: Sequence[ModelMessage], context: Any
    ) -> str:
        prepared = prompt
        for preprocessor in self._preprocessors:
            value = preprocessor(prepared, history, context)
            prepared = await value if inspect.isawaitable(value) else value
            if not isinstance(prepared, str):
                raise TypeError("A prompt preprocessor must return text")
        return prepared

    async def run(
        self,
        prompt: str,
        *,
        history: Sequence[ModelMessage] = (),
        context: Any = None,
    ) -> AgentRunResult[Any]:
        prepared = await self._prepare_prompt(prompt, history, context)
        return await self._agent.run(prepared, message_history=list(history), deps=context)

    @asynccontextmanager
    async def stream(
        self,
        prompt: str,
        *,
        history: Sequence[ModelMessage] = (),
        context: Any = None,
    ) -> AsyncIterator[StreamedRunResult[Any, Any]]:
        prepared = await self._prepare_prompt(prompt, history, context)
        async with self._agent.run_stream(
            prepared, message_history=list(history), deps=context
        ) as result:
            yield result
