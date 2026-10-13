from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from typing import Any

import yaml  # type: ignore[import-untyped]


class PromptError(ValueError):
    """Raised for invalid prompt files or templates."""


class MissingPromptVariable(PromptError):
    """Raised when rendering without all declared variables."""


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    text: str
    source: Path | None = None

    @property
    def variables(self) -> frozenset[str]:
        names: set[str] = set()
        for _, field_name, _, _ in Formatter().parse(self.text):
            if field_name:
                names.add(field_name.split(".", 1)[0].split("[", 1)[0])
        return frozenset(names)

    def render(
        self,
        *,
        variables: Mapping[str, Any] | None = None,
        fragments: Sequence[str] = (),
    ) -> str:
        supplied = dict(variables or {})
        missing = self.variables.difference(supplied)
        if missing:
            raise MissingPromptVariable(f"Missing prompt variables: {', '.join(sorted(missing))}")
        try:
            rendered = self.text.format_map(supplied)
        except (KeyError, ValueError, AttributeError) as exc:
            location = f" in {self.source}" if self.source else ""
            raise PromptError(f"Unable to render prompt{location}: {exc}") from exc
        sections = [
            section.strip() for section in (*fragments, rendered) if section and section.strip()
        ]
        return "\n\n".join(sections)


def load_prompt(
    path: str | Path, *, field: str = "prompt", encoding: str = "utf-8"
) -> PromptTemplate:
    source = Path(path)
    try:
        raw = yaml.safe_load(source.read_text(encoding=encoding))
    except FileNotFoundError as exc:
        raise PromptError(f"Prompt file does not exist: {source}") from exc
    except yaml.YAMLError as exc:
        raise PromptError(f"Invalid YAML in {source}: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise PromptError(f"Prompt file must contain a YAML object: {source}")
    text = raw.get(field)
    if not isinstance(text, str) or not text.strip():
        raise PromptError(f"Prompt field {field!r} must contain non-empty text: {source}")
    return PromptTemplate(text=text.strip(), source=source)
