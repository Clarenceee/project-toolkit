from metaflow import (  # type: ignore[attr-defined]
    environment,
    kubernetes,
    step,
    timeout,
)

from reusable_helpers.shared.config import (
    UNSET,
    parse_bool,
    parse_dict,
    parse_list,
    resolve,
)

_GPU_TOLERATIONS = [{"key": "nvidia.com/gpu", "operator": "Exists", "effect": "NoSchedule"}]


def _parse_tolerations(value):
    # Preserve the original boolean GPU option while also accepting custom lists.
    if isinstance(value, bool) or str(value).lower() in {"true", "false"}:
        return [dict(item) for item in _GPU_TOLERATIONS] if parse_bool(value) else []
    return parse_list(value)


def kubernetes_step(
    cpu=UNSET,
    memory=UNSET,
    run_k8=UNSET,
    tolerations=UNSET,
    secret_name=UNSET,
    additional_env_vars=UNSET,
    timeout_hours=UNSET,
    *,
    image=UNSET,
    namespace=UNSET,
    service_account=UNSET,
    image_pull_secrets=UNSET,
    secrets=UNSET,
    gpu=UNSET,
    **kubernetes_kwargs,
):
    """Register a step, optionally add environment/timeout and remote execution.

    Local execution is the default. Kubernetes settings are read only in remote
    mode. Additional Kubernetes options pass through as keyword arguments.
    """
    run_k8 = resolve(run_k8, env="METAFLOW_RUN_K8", default=False, parser=parse_bool)
    env_vars = resolve(
        additional_env_vars, env="METAFLOW_STEP_ENV_VARS", default={}, parser=parse_dict
    )
    hours = resolve(timeout_hours, env="METAFLOW_STEP_TIMEOUT_HOURS", parser=float)
    if hours is not None and hours <= 0:
        raise ValueError("timeout_hours must be positive")

    remote = {}
    if run_k8:
        raw_tolerations = resolve(tolerations, env="METAFLOW_KUBERNETES_TOLERATIONS", default=[])
        gpu_tolerations = raw_tolerations is True or (
            isinstance(raw_tolerations, str) and raw_tolerations.lower() == "true"
        )
        tolerations = _parse_tolerations(raw_tolerations)
        remote = {
            "image": resolve(image, env="METAFLOW_KUBERNETES_IMAGE", required=True),
            "namespace": resolve(namespace, env="METAFLOW_KUBERNETES_NAMESPACE", required=True),
            "service_account": resolve(
                service_account,
                env="METAFLOW_KUBERNETES_SERVICE_ACCOUNT",
                required=True,
            ),
            "cpu": resolve(cpu, env="METAFLOW_KUBERNETES_CPU", default=1, parser=float),
            "memory": resolve(memory, env="METAFLOW_KUBERNETES_MEMORY", default=256, parser=int),
            "gpu": resolve(
                gpu,
                env="METAFLOW_KUBERNETES_GPU",
                default=1 if gpu_tolerations else 0,
                parser=int,
            ),
            "image_pull_secrets": resolve(
                image_pull_secrets,
                env="METAFLOW_KUBERNETES_IMAGE_PULL_SECRETS",
                default=[],
                parser=parse_list,
            ),
            "secrets": resolve(
                secrets,
                env="METAFLOW_KUBERNETES_SECRETS",
                default=[],
                parser=parse_list,
            ),
        }
        if remote["cpu"] <= 0 or remote["memory"] <= 0 or remote["gpu"] < 0:
            raise ValueError("cpu/memory must be positive and gpu must be nonnegative")
        extra_secret = resolve(secret_name, env="METAFLOW_STEP_SECRET_NAME")
        if extra_secret:
            remote["secrets"] = [*remote["secrets"], extra_secret]
        if tolerations:
            if any(not isinstance(item, dict) for item in tolerations):
                raise ValueError("tolerations must be a list of objects")
            remote["tolerations"] = tolerations
        remote.update(kubernetes_kwargs)

    def decorator(func):
        func = step(func)
        if env_vars:
            func = environment(vars=env_vars)(func)
        if run_k8:
            func = kubernetes(**remote)(func)
        if hours is not None:
            func = timeout(seconds=int(hours * 3600))(func)
        return func

    return decorator
