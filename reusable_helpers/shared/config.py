import json
import os
from typing import Any, Callable


class _Unset:
    pass


UNSET = _Unset()


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise ValueError("expected true/false, yes/no, on/off, or 1/0")


def parse_list(value: Any) -> list:
    if isinstance(value, (list, tuple)):
        return list(value)
    if str(value).lstrip().startswith("["):
        result = json.loads(value)
        if not isinstance(result, list):
            raise ValueError("expected a JSON list")
        return result
    return [item.strip() for item in str(value).split(",") if item.strip()]


def parse_dict(value: Any) -> dict:
    result = json.loads(value) if isinstance(value, str) else value
    if not isinstance(result, dict):
        raise ValueError("expected a JSON object")
    return dict(result)


def resolve(
    value=UNSET,
    *,
    env: str,
    default=None,
    parser: Callable | None = None,
    required: bool = False,
):
    """Resolve one setting without dropping explicit False, zero, or empty lists."""
    result = os.environ.get(env, default) if value is UNSET else value
    if required and (result is None or result == ""):
        raise ValueError(f"{env} is required; pass an argument or set the environment variable")
    if result is None:
        return None
    try:
        return parser(result) if parser else result
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {env}: {exc}") from exc
