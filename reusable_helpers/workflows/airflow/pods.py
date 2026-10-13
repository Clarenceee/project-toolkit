import json
from datetime import timedelta

from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s

from reusable_helpers.shared.config import (
    UNSET,
    parse_bool,
    parse_dict,
    parse_list,
    resolve,
)


def serialize_env_value(value):
    return json.dumps(value) if isinstance(value, (dict, list)) else str(value)


def get_kubernetes_pod_operator(
    task_id: str,
    image=UNSET,
    name=None,
    env_vars=UNSET,
    cmds=None,
    image_pull_policy=UNSET,
    retries=UNSET,
    retry_delay=UNSET,
    execution_timeout=UNSET,
    is_delete_operator_pod=UNSET,
    get_logs=UNSET,
    in_cluster=UNSET,
    is_serialize_env_value=True,
    *,
    namespace=UNSET,
    service_account_name=UNSET,
    image_pull_secrets=UNSET,
    **kwargs,
):
    vars_ = resolve(env_vars, env="AIRFLOW_POD_ENV_VARS", default={}, parser=parse_dict)
    pull_secrets = resolve(
        image_pull_secrets,
        env="AIRFLOW_POD_IMAGE_PULL_SECRETS",
        default=[],
        parser=parse_list,
    )
    return KubernetesPodOperator(
        task_id=task_id,
        name=name or task_id,
        image=resolve(image, env="AIRFLOW_POD_IMAGE", required=True),
        cmds=cmds,
        namespace=resolve(namespace, env="AIRFLOW_POD_NAMESPACE", required=True),
        service_account_name=resolve(
            service_account_name, env="AIRFLOW_POD_SERVICE_ACCOUNT", required=True
        ),
        env_vars=[
            k8s.V1EnvVar(
                name=str(key),
                value=serialize_env_value(value) if is_serialize_env_value else str(value),
            )
            for key, value in vars_.items()
        ],
        image_pull_secrets=[k8s.V1LocalObjectReference(name=name) for name in pull_secrets],
        image_pull_policy=resolve(
            image_pull_policy,
            env="AIRFLOW_POD_IMAGE_PULL_POLICY",
            default="IfNotPresent",
        ),
        retries=resolve(retries, env="AIRFLOW_POD_RETRIES", default=1, parser=int),
        retry_delay=(
            timedelta(
                seconds=resolve(env="AIRFLOW_POD_RETRY_DELAY_SECONDS", default=30, parser=float)
            )
            if retry_delay is UNSET
            else retry_delay
        ),
        execution_timeout=(
            timedelta(
                seconds=resolve(env="AIRFLOW_POD_TIMEOUT_SECONDS", default=1800, parser=float)
            )
            if execution_timeout is UNSET
            else execution_timeout
        ),
        on_finish_action=(
            "delete_pod"
            if resolve(
                is_delete_operator_pod,
                env="AIRFLOW_POD_DELETE_ON_FINISH",
                default=True,
                parser=parse_bool,
            )
            else "keep_pod"
        ),
        get_logs=resolve(get_logs, env="AIRFLOW_POD_GET_LOGS", default=True, parser=parse_bool),
        in_cluster=resolve(
            in_cluster, env="AIRFLOW_POD_IN_CLUSTER", default=True, parser=parse_bool
        ),
        **kwargs,
    )
