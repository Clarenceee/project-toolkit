from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class Memory:
    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    score: float | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Memory text must not be empty")


@dataclass(frozen=True, slots=True)
class MemoryRecallRequest:
    query: str
    subject_id: str
    namespace: str | None = None
    filters: Mapping[str, Any] = field(default_factory=dict)
    limit: int | None = None

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("Recall query must not be empty")
        if not self.subject_id.strip():
            raise ValueError("subject_id must not be empty")
        if self.limit is not None and self.limit < 1:
            raise ValueError("limit must be positive")


class MemoryProvider(Protocol):
    async def recall(self, request: MemoryRecallRequest) -> Sequence[Memory]: ...


MemoryFormatter = Callable[[Sequence[Memory]], str]


def format_memory_bullets(memories: Sequence[Memory]) -> str:
    unique = list(dict.fromkeys(memory.text.strip() for memory in memories))
    return "\n".join(f"- {text}" for text in unique)


class MemoryContext:
    def __init__(
        self,
        provider: MemoryProvider,
        *,
        formatter: MemoryFormatter = format_memory_bullets,
        heading: str = "Relevant memory",
    ) -> None:
        self._provider = provider
        self._formatter = formatter
        self._heading = heading

    async def recall(
        self,
        *,
        query: str,
        subject_id: str,
        namespace: str | None = None,
        filters: Mapping[str, Any] | None = None,
        limit: int | None = None,
    ) -> tuple[Memory, ...]:
        result = await self._provider.recall(
            MemoryRecallRequest(
                query=query,
                subject_id=subject_id,
                namespace=namespace,
                filters=dict(filters or {}),
                limit=limit,
            )
        )
        return tuple(result)

    def render(self, memories: Sequence[Memory]) -> str:
        if not memories:
            return ""
        body = self._formatter(memories).strip()
        return f"## {self._heading}\n{body}" if body else ""


class InMemoryMemoryProvider:
    """Simple memory adapter for tests and local examples."""

    def __init__(self, memories_by_subject: Mapping[str, Sequence[Memory]] | None = None) -> None:
        self._memories = {
            subject_id: tuple(memories)
            for subject_id, memories in (memories_by_subject or {}).items()
        }

    async def recall(self, request: MemoryRecallRequest) -> Sequence[Memory]:
        memories = self._memories.get(request.subject_id, ())
        if request.namespace is not None:
            memories = tuple(
                memory
                for memory in memories
                if memory.metadata.get("namespace") == request.namespace
            )
        if request.filters:
            memories = tuple(
                memory
                for memory in memories
                if all(
                    key in memory.metadata and memory.metadata[key] == value
                    for key, value in request.filters.items()
                )
            )
        return memories[: request.limit]
