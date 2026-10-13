# PyFlink Kafka starter

Copy this directory into a consuming project, then adapt `mock_process` in `service/main.py` to
its event schema. The job reads UTF-8 JSON objects from one Kafka topic, applies a
pure transform, and writes JSON strings to another topic. It uses at-least-once
delivery and starts from the consumer group's committed offsets, or the earliest
offset when the group is new.

## Choose versions and build

Select a Flink release with a matching PyFlink package and a supported Python
interpreter. The `FLINK_VERSION` build argument sets both the base image tag and
PyFlink package version. Check that the image's Linux package repository provides
a Python version supported by that Flink release. Add the matching Kafka connector
JAR to the consuming project's image or deployment package; PyFlink alone does not
include it.

```bash
docker build --build-arg FLINK_VERSION=<flink-version> -t my-flink-job .
```

The Dockerfile is a starting point. Set the Python client and worker interpreters
explicitly in the deployment when the runtime cannot discover `/opt/flink/venv/bin/python`.

## Configure and run

Copy `.env.example` to a local environment file and set the broker, topics, and
group ID. These values are for local development only. The job reads environment
variables from its process; a `.env` file is not loaded automatically. For a
local standalone Flink cluster, pass the variables to the process that submits
the job and run its Python entry point:

```bash
PYTHONPATH="$PWD" flink run -py service/main.py
```

| Setting | Required | Default |
| --- | --- | --- |
| `KAFKA_BOOTSTRAP_SERVERS` | Yes | None |
| `KAFKA_SOURCE_TOPIC` | Yes | None |
| `KAFKA_SINK_TOPIC` | Yes | None |
| `KAFKA_GROUP_ID` | No | Job name |
| `FLINK_JOB_NAME` | No | `flink-example` |
| `FLINK_PARALLELISM` | No | `1`, must be positive |

For a smoke test, publish `{"event_id":"demo-1","value":42}` to the source topic.
The sink topic should receive
`{"event_id":"demo-1","processed_by":"flink","value":42}`.
The pure transformation can also be checked without Flink or Kafka:

```bash
python -c 'from service.main import mock_process; print(mock_process("{\"event_id\":\"demo-1\",\"value\":42}"))'
```

## Adapt before production

- Choose compatible Flink, PyFlink, Python, Kafka connector, and broker versions.
- Supply Kafka authentication and authorization through the consuming project's
  runtime secrets and client configuration. Never put credentials in this template.
- Configure durable checkpoint storage, recovery, and any high availability needs
  in the deployment. Verify the selected Kafka sink guarantee matches those settings.
- Decide how malformed records should be handled; the starter currently fails the
  job on invalid JSON.
- Set operator UIDs before the first stateful deployment and preserve them across
  upgrades. Add lag, throughput, checkpoint, restart, and sink failure monitoring.
- Test cancellation, restart, recovery, schema changes, and credential rotation.

The consuming project owns its image registry, topics, schemas, secrets, models,
service account, and deployment manifests. This template does not install or
configure the Flink Kubernetes Operator or Helm chart.
