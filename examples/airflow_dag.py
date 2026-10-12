from datetime import datetime, timezone

from reusable_helpers.workflows.airflow.dags import get_dag
from reusable_helpers.workflows.airflow.pods import get_kubernetes_pod_operator


@get_dag(
    dag_id="example_task",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule=None,
    tags=["example"],
)
def example_dag():
    return get_kubernetes_pod_operator(
        task_id="hello",
        cmds=["python", "-c"],
        arguments=["print('Hello from Project Toolkit')"],
        env_vars={},
    )


dag = example_dag()
