# Deployment template guidance

Keep `apps/dev/` limited to child applications that the base should actually
deploy. Put optional workload applications under `examples/` until a consuming
project has supplied real values and deliberately activates them.

Keep environment-owned settings under `values/<component>/`, and use Secrets or
External Secrets for credentials. Do not commit credential values, real account
identifiers, private endpoints, or organization-specific image registries to
this template.

Run `make lint` and `make render` from this directory after changing a chart.
Use ArgoCD as the deployment source of truth; the scripts only compare or apply
the root App-of-Apps.
