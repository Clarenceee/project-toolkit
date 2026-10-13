import argparse

from reusable_helpers.shared.config import UNSET
from reusable_helpers.workflows.metaflow.airflow import generate_dag


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flow", required=True)
    parser.add_argument("--output", default=UNSET)
    parser.add_argument("--deploy", action=argparse.BooleanOptionalAction, default=UNSET)
    parser.add_argument("--retry", action=argparse.BooleanOptionalAction, default=UNSET)
    parser.add_argument("--paused", action=argparse.BooleanOptionalAction, default=UNSET)
    parser.add_argument("--authorize", default=UNSET)
    parser.add_argument("--python", default=UNSET)
    parser.add_argument("--dag-id", default=UNSET)
    parser.add_argument("--start-date", default=UNSET)
    parser.add_argument("--execution-timeout", type=int, default=UNSET)
    parser.add_argument("--startup-timeout", type=int, default=UNSET)
    parser.add_argument("--tags", nargs="*", default=UNSET)
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE")
    args = parser.parse_args()
    env = {}
    for setting in args.env:
        key, separator, value = setting.partition("=")
        if not separator or not key:
            parser.error("--env expects KEY=VALUE")
        env[key] = value
    output = generate_dag(
        args.flow,
        args.output,
        args.deploy,
        args.authorize,
        env_overrides=env,
        dag_id=args.dag_id,
        start_date=args.start_date,
        execution_timeout=args.execution_timeout,
        startup_timeout=args.startup_timeout,
        tags=args.tags,
        retry=args.retry,
        paused=args.paused,
        python=args.python,
    )
    print(f"DAG written to {output}")


if __name__ == "__main__":
    main()
