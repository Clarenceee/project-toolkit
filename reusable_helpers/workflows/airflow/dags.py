from datetime import timedelta

from airflow.decorators import dag

from reusable_helpers.shared.config import UNSET, parse_bool, parse_list, resolve


def get_default_dag_args(*, owner=UNSET, retries=UNSET, retry_delay_seconds=UNSET):
    return {
        "owner": resolve(owner, env="AIRFLOW_DAG_OWNER", default="data-engineer"),
        "retries": resolve(retries, env="AIRFLOW_DAG_RETRIES", default=2, parser=int),
        "retry_delay": timedelta(
            seconds=resolve(
                retry_delay_seconds,
                env="AIRFLOW_DAG_RETRY_DELAY_SECONDS",
                default=300,
                parser=float,
            )
        ),
    }


def get_dag(
    dag_id: str,
    *,
    start_date,
    schedule=UNSET,
    catchup=UNSET,
    concurrency=UNSET,
    tags=UNSET,
    default_args=UNSET,
    dagrun_timeout=UNSET,
    **kwargs,
):
    """Use a caller-owned fixed start date; callbacks can be passed in kwargs."""
    args = get_default_dag_args() if default_args is UNSET else default_args
    limit = dagrun_timeout
    if limit is UNSET:
        seconds = resolve(
            env="AIRFLOW_DAG_TIMEOUT_SECONDS", default=14400, parser=float
        )
        limit = timedelta(seconds=seconds) if seconds is not None else None
    return dag(
        dag_id=dag_id,
        start_date=start_date,
        schedule=resolve(schedule, env="AIRFLOW_DAG_SCHEDULE"),
        catchup=resolve(
            catchup, env="AIRFLOW_DAG_CATCHUP", default=False, parser=parse_bool
        ),
        max_active_tasks=resolve(
            concurrency, env="AIRFLOW_DAG_MAX_ACTIVE_TASKS", default=5, parser=int
        ),
        tags=resolve(tags, env="AIRFLOW_DAG_TAGS", default=[], parser=parse_list),
        default_args=args,
        dagrun_timeout=limit,
        **kwargs,
    )
