"""Register a text file as an MLflow prompt when its contents change."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from reusable_helpers.observability.mlflow_prompt_registry import MlflowPromptRegistry


def _json_object(value: str) -> dict:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("expected a JSON object")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="MLflow prompt name")
    parser.add_argument("path", type=Path, help="UTF-8 text file containing the prompt")
    parser.add_argument("--commit-message", default="Update prompt")
    parser.add_argument("--metadata", type=_json_object)
    parser.add_argument("--tag", action="append", default=[], metavar="KEY=VALUE")
    args = parser.parse_args()
    try:
        tags = dict(item.split("=", 1) for item in args.tag)
    except ValueError:
        parser.error("--tag values must use KEY=VALUE syntax")
    result = MlflowPromptRegistry().register_if_changed(
        name=args.name,
        template=args.path.read_text(encoding="utf-8"),
        commit_message=args.commit_message,
        metadata=args.metadata,
        tags=tags,
    )
    action = "registered" if result.created else "unchanged"
    print(f"{action}: {result.prompt.name} version {result.prompt.version}")


if __name__ == "__main__":
    main()
