# FlinkDeployment Helm starter

This chart renders one `FlinkDeployment` for the Flink Kubernetes Operator. It is
separate from the [PyFlink Kafka application starter](../../../templates/flink/README.md).
The consuming project supplies an image, Flink version, Python driver JAR path,
checkpoint storage, service account, and Kafka configuration through its own
values file and runtime Secrets.

Copy `values.example.yaml` into the consuming project's environment values files
and replace every `replace-...` or `REPLACE_...` value. The example deliberately
contains no working registry, storage location, credentials, or pinned release.
The `flinkDeploymentSpec` map is passed to the operator CRD as the job's spec;
the chart validates its required image, version, and Python job fields.

Validate the chart before applying it:

```bash
helm lint deployment/charts/flink-helm -f deployment/charts/flink-helm/values.example.yaml
helm template example deployment/charts/flink-helm -f deployment/charts/flink-helm/values.example.yaml
```

For a real deployment, use a completed environment values file instead of the
example. Install the Flink Kubernetes Operator and provision its namespace,
service account, Secrets, and durable checkpoint storage before installing the
job chart. Build and publish the application image and include a Kafka connector
JAR compatible with the chosen Flink release. Keep credential values out of Git.

Optional ingress is disabled by default. When enabled, set `ingress.host`, the
ingress class and TLS settings appropriate to the cluster. The default backend
service name is `<FlinkDeployment name>-rest`; override `ingress.serviceName`
if the operator creates a different service name. Review access control before
exposing the Flink REST endpoint.
