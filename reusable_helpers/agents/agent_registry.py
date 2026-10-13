from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

AgentT = TypeVar("AgentT")
AgentBuilder = Callable[..., AgentT]


class AgentRegistryError(Exception):
    """Base error for registry operations."""


class DuplicateAgentError(AgentRegistryError):
    """Raised when registering an existing name without replacement."""


class UnknownAgentError(AgentRegistryError):
    """Raised when looking up an unregistered agent."""


@dataclass(frozen=True, slots=True)
class AgentSpec(Generic[AgentT]):
    name: str
    builder: AgentBuilder[AgentT]
    description: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Agent name must not be empty")


class AgentRegistry(Generic[AgentT]):
    def __init__(self) -> None:
        self._specs: dict[str, AgentSpec[AgentT]] = {}

    def register(self, spec: AgentSpec[AgentT], *, replace: bool = False) -> None:
        if spec.name in self._specs and not replace:
            raise DuplicateAgentError(f"Agent {spec.name!r} is already registered")
        self._specs[spec.name] = spec

    def unregister(self, name: str) -> AgentSpec[AgentT]:
        try:
            return self._specs.pop(name)
        except KeyError as exc:
            raise UnknownAgentError(f"Unknown agent: {name!r}") from exc

    def get(self, name: str) -> AgentSpec[AgentT]:
        try:
            return self._specs[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._specs)) or "<none>"
            raise UnknownAgentError(f"Unknown agent {name!r}; available: {available}") from exc

    def build(self, name: str, /, **kwargs: Any) -> AgentT:
        return self.get(name).builder(**kwargs)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._specs))

    def __contains__(self, name: object) -> bool:
        return name in self._specs

    def __iter__(self) -> Iterator[AgentSpec[AgentT]]:
        return iter(self._specs[name] for name in sorted(self._specs))

    def __len__(self) -> int:
        return len(self._specs)
