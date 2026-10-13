"""Register changed prompt templates and retrieve the latest version."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PromptVersion:
    name: str
    version: int
    template: str


@dataclass(frozen=True, slots=True)
class PromptRegistration:
    prompt: PromptVersion
    created: bool


class MlflowPromptRegistry:
    def __init__(self, mlflow_module: Any | None = None) -> None:
        self._mlflow: Any = mlflow_module
        if mlflow_module is None:
            import mlflow

            self._mlflow = mlflow

    def get_latest(self, name: str) -> PromptVersion | None:
        if not name.strip():
            raise ValueError("Prompt name must not be empty")
        try:
            prompt = self._mlflow.load_prompt(f"prompts:/{name}/latest")
        except Exception as exc:
            if self._is_missing_prompt(exc):
                return None
            raise
        return PromptVersion(
            name=prompt.name,
            version=int(prompt.version),
            template=prompt.template,
        )

    def register_if_changed(
        self,
        *,
        name: str,
        template: str,
        commit_message: str,
        metadata: Mapping[str, Any] | None = None,
        tags: Mapping[str, str] | None = None,
    ) -> PromptRegistration:
        if not name.strip():
            raise ValueError("Prompt name must not be empty")
        if not template.strip():
            raise ValueError("Prompt template must not be empty")
        current = self.get_latest(name)
        if current is not None and current.template == template:
            return PromptRegistration(prompt=current, created=False)
        created = self._mlflow.register_prompt(
            name=name,
            template=template,
            commit_message=commit_message,
            version_metadata=dict(metadata or {}),
            tags=dict(tags or {}),
        )
        return PromptRegistration(
            prompt=PromptVersion(
                name=created.name,
                version=int(created.version),
                template=created.template,
            ),
            created=True,
        )

    @staticmethod
    def _is_missing_prompt(exc: Exception) -> bool:
        message = str(exc).casefold()
        markers = ("not found", "does not exist", "resource does not exist")
        return any(marker in message for marker in markers)
