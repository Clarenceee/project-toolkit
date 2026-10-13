"""Log a caller-supplied Python model to MLflow."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentLogRequest:
    experiment_name: str
    artifact_path: str
    python_model: Any
    code_paths: Sequence[str] = ()
    prompts: Sequence[Any] = ()
    parameters: Mapping[str, Any] = field(default_factory=dict)
    tags: Mapping[str, str] = field(default_factory=dict)
    run_name: str | None = None
    registered_model_name: str | None = None

    def __post_init__(self) -> None:
        if not self.experiment_name.strip():
            raise ValueError("experiment_name must not be empty")
        if not self.artifact_path.strip():
            raise ValueError("artifact_path must not be empty")


@dataclass(frozen=True, slots=True)
class AgentLogResult:
    run_id: str
    model_uri: str


class MlflowAgentLogger:
    def __init__(self, mlflow_module: Any | None = None) -> None:
        self._mlflow: Any = mlflow_module
        if mlflow_module is None:
            import mlflow

            self._mlflow = mlflow

    def log(self, request: AgentLogRequest) -> AgentLogResult:
        self._mlflow.set_experiment(request.experiment_name)
        with self._mlflow.start_run(run_name=request.run_name) as run:
            if request.parameters:
                self._mlflow.log_params(dict(request.parameters))
            for key, value in request.tags.items():
                self._mlflow.set_tag(key, value)
            model_info = self._mlflow.pyfunc.log_model(
                artifact_path=request.artifact_path,
                python_model=request.python_model,
                code_paths=list(request.code_paths) or None,
                prompts=list(request.prompts) or None,
                registered_model_name=request.registered_model_name,
            )
            model_uri = getattr(
                model_info, "model_uri", f"runs:/{run.info.run_id}/{request.artifact_path}"
            )
            return AgentLogResult(run_id=run.info.run_id, model_uri=model_uri)
