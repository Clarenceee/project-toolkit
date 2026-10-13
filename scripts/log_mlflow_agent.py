"""Log an importable MLflow PythonModel object through the toolkit adapter."""

from __future__ import annotations

import argparse
import importlib
import json

from reusable_helpers.observability.mlflow_agent_logger import AgentLogRequest, MlflowAgentLogger


def _json_object(value: str) -> dict:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("expected a JSON object")
    return parsed


def _load_object(path: str):
    module_name, separator, attribute = path.partition(":")
    if not separator or not module_name or not attribute:
        raise argparse.ArgumentTypeError("model must use module:attribute syntax")
    try:
        return getattr(importlib.import_module(module_name), attribute)
    except (ImportError, AttributeError) as exc:
        raise argparse.ArgumentTypeError(f"cannot load model {path!r}: {exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment")
    parser.add_argument("artifact_path")
    parser.add_argument(
        "model",
        type=_load_object,
        help="Import path to a PythonModel object: module:attribute",
    )
    parser.add_argument("--run-name")
    parser.add_argument("--registered-model-name")
    parser.add_argument("--code-path", action="append", default=[])
    parser.add_argument("--parameters", type=_json_object)
    parser.add_argument("--tag", action="append", default=[], metavar="KEY=VALUE")
    args = parser.parse_args()
    try:
        tags = dict(item.split("=", 1) for item in args.tag)
    except ValueError:
        parser.error("--tag values must use KEY=VALUE syntax")
    result = MlflowAgentLogger().log(
        AgentLogRequest(
            experiment_name=args.experiment,
            artifact_path=args.artifact_path,
            python_model=args.model,
            code_paths=args.code_path,
            parameters=args.parameters,
            tags=tags,
            run_name=args.run_name,
            registered_model_name=args.registered_model_name,
        )
    )
    print(f"logged run {result.run_id}: {result.model_uri}")


if __name__ == "__main__":
    main()
