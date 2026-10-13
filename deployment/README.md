# Helm Charts Deployment Base Template

This is a starting point for a separate GitOps repository. ArgoCD owns deployment
after the root App-of-Apps is applied. The default environment is `dev`; the base
contains no business workload application. It includes three chart templates:

- `charts/generic-helm/` renders a simple stateless Deployment and optional
  ServiceAccount.
- `charts/ray-service/` renders a KubeRay `RayService`.
- `charts/flink-helm/` renders a Flink Operator `FlinkDeployment` and optional
  ingress. See its [README](charts/flink-helm/README.md).

The [Notion base template](https://app.notion.com/p/3f854f16413781dab4bdce2dd9f25a64)
is the source for the repository layout and examples. The Ray application is in
`examples/ray-service/`, outside `apps/dev/`, so the App-of-Apps does not deploy it
until a consuming project chooses to copy it into that directory.

## Start a consuming repository

Copy the contents of `deployment/` into the root of the deployment repository.
Before connecting ArgoCD, replace the example repository URLs in `apps/`, choose
the External Secrets Operator chart version, and review every environment-owned
setting. The example URLs and image names are placeholders and cannot deploy.

The only child application present in `apps/dev/` installs External Secrets
Operator from its upstream chart. The generic, Ray, and Flink chart examples are
validated locally but are not activated by the App-of-Apps. Add their ArgoCD
Application files to `apps/dev/` only after their image, namespace, service
account, secrets, and other required resources are ready.

Run local validation from this directory:

```bash
make lint
make render
```

`make render` produces example YAML with deliberately invalid placeholder values.
It checks chart rendering, not cluster readiness. To compare or apply the dev
root application after configuring the repository and selecting a cluster:

```bash
make diff ENV=dev
make deploy ENV=dev
```

`diff` runs `kubectl diff`; exit status 1 means there are differences. `deploy`
applies only `apps/dev-applications.yaml`. ArgoCD then reconciles its child
Applications from `apps/dev/`.

## Template map

| Path | Purpose | Active in the dev App-of-Apps? |
| --- | --- | --- |
| `apps/dev-applications.yaml` | Root App-of-Apps | Applied manually once |
| `apps/dev/external-secrets.yaml` | Upstream operator child application | Yes |
| `values/external-secrets/dev-values.yaml` | Operator environment values | Yes |
| `charts/generic-helm/` and `values/generic-platform/` | Stateless chart example | No |
| `charts/ray-service/`, `values/platform-example/`, `examples/ray-service/` | RayService chart and opt-in application | No |
| `charts/flink-helm/` | Flink job chart | No |
| `secrets/` and `manifests/` | ExternalSecret and raw manifest examples | No |

The ExternalSecret example requires a configured `ClusterSecretStore`, and its
secret name and remote key must be replaced. The ServiceAccount example contains
an IAM role placeholder. Keep secret values out of Git. Add a separate ArgoCD
Application or another deliberate sync path for raw manifests when needed.

## Add staging or production

Create `apps/<environment>-applications.yaml` and `apps/<environment>/` for each
new environment. Copy only the values and manifests needed there, then review
namespaces, repository revisions, image tags, Secret Manager keys, IAM roles,
node selectors, storage paths, and resource sizing. Each environment needs its
own root App-of-Apps source path and application names.

Deployment order: ArgoCD → root App-of-Apps → platform operators → referenced
Secrets and service accounts → workload applications. Install KubeRay or the
Flink Kubernetes Operator before adding the corresponding custom resource chart.
