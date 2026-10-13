import ast
import os
import re
import subprocess  # nosec B404 - required to run the caller's Metaflow flow
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from reusable_helpers.shared.config import UNSET, parse_bool, parse_list, resolve


def patch_config(dag_path: Path, patches: dict) -> None:
    """Apply all requested patches or fail without writing a partially patched file."""
    content = dag_path.read_text()
    for name, patch in patches.items():
        replacement = patch["replacement"]

        def replace(_match: re.Match[str], replacement: str = replacement) -> str:
            return replacement

        content, count = re.subn(
            patch["pattern"],
            replace,
            content,
        )
        if count == 0 or (patch.get("unique", True) and count != 1):
            raise ValueError(
                f"Unexpected match count for {name}: {count}; generated DAG format may differ"
            )
    ast.parse(content, filename=str(dag_path))
    dag_path.write_text(content)


def get_patch_config(
    *,
    dag_id=None,
    start_date=None,
    execution_timeout=None,
    startup_timeout=None,
    tags=None,
) -> dict:
    """Optional patches for the dictionary CONFIG format used in the source doc.

    These patches are intentionally strict about the generated file structure.
    Unsupported formats raise an error instead of silently producing bad output.
    """
    patches: dict = {}
    if dag_id is not None:
        patches["dag_id"] = {
            "pattern": r"['\"]dag_id['\"]:\s*['\"][^'\"]+['\"]",
            "replacement": f"'dag_id': {dag_id!r}",
        }
    if start_date is not None:
        date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00")
        patches["start_date"] = {
            "pattern": r"['\"]start_date['\"]:\s*['\"][^'\"]+['\"]",
            "replacement": f"'start_date': {date!r}",
        }
    if execution_timeout is not None:
        if execution_timeout <= 0:
            raise ValueError("execution_timeout must be positive")
        patches["execution_timeout"] = {
            "pattern": r"['\"]execution_timeout['\"]:\s*\{['\"]seconds['\"]:\s*\d+(?:\.\d+)?\}",
            "replacement": f"'execution_timeout': {{'seconds': {execution_timeout}}}",
            "unique": False,
        }
    if startup_timeout is not None:
        if startup_timeout <= 0:
            raise ValueError("startup_timeout must be positive")
        patches["startup_timeout"] = {
            "pattern": r"['\"]startup_timeout_seconds['\"]:\s*\d+",
            "replacement": f"'startup_timeout_seconds': {startup_timeout}",
            "unique": False,
        }
    if tags is not None:
        patches["tags"] = {
            "pattern": r"['\"]tags['\"]:\s*(?:\([^)]*\)|\[[^]]*\])",
            "replacement": f"'tags': {list(tags)!r}",
        }
    return patches


def generate_dag(
    flow_file,
    dag_file=UNSET,
    deploy=UNSET,
    authorize=UNSET,
    *,
    env_overrides=None,
    dag_id=UNSET,
    start_date=UNSET,
    execution_timeout=UNSET,
    startup_timeout=UNSET,
    tags=UNSET,
    retry=UNSET,
    paused=UNSET,
    python=UNSET,
) -> Path:
    """Generate a DAG via Metaflow; configuration remains owned by the caller.

    Metaflow generation may contact its configured datastore/backend. It is
    separate from running a flow locally and needs the caller's backend setup.
    """
    flow = Path(flow_file).resolve(strict=True)
    output = Path(
        resolve(dag_file, env="METAFLOW_DAG_OUTPUT", default=f"{flow.stem}_dag.py")
    ).resolve()
    if flow == output:
        raise ValueError("DAG output must differ from the source flow")
    patches = get_patch_config(
        dag_id=resolve(dag_id, env="METAFLOW_DAG_ID"),
        start_date=resolve(start_date, env="METAFLOW_DAG_START_DATE"),
        execution_timeout=resolve(
            execution_timeout, env="METAFLOW_DAG_EXECUTION_TIMEOUT", parser=int
        ),
        startup_timeout=resolve(startup_timeout, env="METAFLOW_DAG_STARTUP_TIMEOUT", parser=int),
        tags=resolve(tags, env="METAFLOW_DAG_TAGS", parser=parse_list),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    # A temporary directory protects existing output if generation or patching fails.
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        temporary = Path(directory) / output.name
        cmd = [
            resolve(python, env="METAFLOW_DAG_PYTHON", default=sys.executable),
            str(flow),
        ]
        if resolve(deploy, env="METAFLOW_DAG_PRODUCTION", default=False, parser=parse_bool):
            cmd.append("--production")
        if resolve(retry, env="METAFLOW_DAG_RETRY", default=True, parser=parse_bool):
            cmd.extend(["--with", "retry"])
        cmd.extend(["airflow", "create", str(temporary)])
        if resolve(paused, env="METAFLOW_DAG_PAUSED", default=True, parser=parse_bool):
            cmd.append("--is-paused-upon-creation")
        token = resolve(authorize, env="METAFLOW_DAG_AUTHORIZE")
        if token is not None:
            cmd.extend(["--authorize", token])
        child_env = {
            **os.environ,
            **{key: str(value) for key, value in (env_overrides or {}).items()},
        }
        # Deliberate execution of the caller's flow; arguments never use a shell.
        subprocess.run(cmd, check=True, env=child_env)  # nosec B603
        patch_config(temporary, patches)
        temporary.replace(output)
    return output
