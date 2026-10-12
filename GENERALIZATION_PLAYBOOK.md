# Playbook: adding reusable code

Use this process when moving code from an application, notebook, or document into the repository.

## 1. Define the reusable operation

Describe the helper in one sentence: what it accepts, what it does, and what it returns. Identify which parts are business logic, reusable behavior, and deployment configuration.

For example, extract “create a configurable Kubernetes-backed Metaflow step” from a customer-ingestion flow. Keep customer models, table names, screening rules, and ingestion orchestration in the consuming project.

Keep an internal source reference where useful. Examples and documentation should demonstrate the general operation with synthetic inputs.

## 2. Choose the right destination

- Put importable behavior under the relevant `reusable_helpers/` capability.
- Put genuinely cross-capability utilities under `shared/`.
- Put command-line entry scripts under `scripts/`; keep reusable logic in helper modules.
- Put project-specific starting files under `templates/`.
- Put runnable demonstrations under `examples/`.

Prefer existing modules when the responsibility fits. Extract shared code when multiple capabilities need the same behavior; do not create a generic utility layer merely because two functions look similar.

## 3. Remove application assumptions

Inspect literals, imports, file paths, generated commands, and defaults for:

- Organization names, account IDs, endpoints, registries, bucket names and cluster resources.
- Personal paths, fixed repository layouts and developer usernames.
- Domain models, SQL tables, index names and workflow-specific constants.
- Hidden imports from the originating application.
- Credential logging, implicit clients and network calls at import time.

Replace configurable settings with explicit arguments and environment fallbacks. Replace application behavior with caller-supplied inputs or narrowly defined callbacks. Remove pieces that cannot be separated cleanly from the source application's business logic.

## 4. Make configuration predictable

For every setting, document:

| Field | Required information |
| --- | --- |
| Argument | Name and accepted type |
| Environment | Variable name and text format |
| Default | General value, or no default |
| Validation | Valid values and error conditions |
| Execution mode | When the setting is required |

Apply the same precedence everywhere: explicit argument → environment variable → general default. All settings allow explicit overrides.

Use the shared parser for booleans, numbers, lists, and required values. Reject invalid values with an error identifying the setting. Honor explicit falsy values and distinguish an omitted argument from an intentionally supplied `None` where needed. Avoid mutable defaults such as `{}` and `[]`.

Infrastructure settings have no organization-specific default. Read existing framework environment variables when appropriate instead of inventing duplicate settings. Do not overwrite unrelated environment variables or forward the entire process environment to remote tasks; accept an explicit set of values to forward.

Example intended behavior:

```python
# Proposed API: local execution needs no Kubernetes configuration.
@kubernetes_step()
def start(self):
    self.next(self.end)

# Explicit arguments override corresponding environment settings.
@kubernetes_step(run_k8=True, cpu=4, namespace="example-jobs")
def process(self):
    self.next(self.end)
```

Kubernetes image and other required settings can come from env or explicit arguments. Missing required settings fail only when Kubernetes is requested.

## 5. Keep dependencies and imports controlled

Add any new third-party runtime dependency to the single root `pyproject.toml` with `uv add`. Add development tools with `uv add --dev`. Resolve the complete list and commit `uv.lock` before accepting the change, because every consuming project installs all runtime dependencies. Run `make format` and `make check` before sharing changes.

Import through `reusable_helpers`, not through the originating project's `src` modules. Keep root imports lightweight. Do not introduce cycles or make `shared/` depend on integrations.

Document supported dependency versions and any compatibility limitation. For generated framework code, validate the supported output structure and report unsupported formats clearly. Avoid unexplained text replacements tied to one project's generated output.

## 6. Provide a complete example

Add an example with synthetic inputs, the exact run command, expected output, and any required environment variable names. Add placeholders to `.env.example`; never commit live credential values.

Show the consuming-project import path through the `reusable/` submodule. If remote execution is involved, explain how the source files reach the worker or container. A successful local import does not establish that remote imports work.

For templates, mark every field the consuming project must adapt. Migration history and application models remain in that project.

## 7. Validate the reusable contract

Use focused checks for behavior that can regress: configuration precedence, invalid inputs, boundary cases, output contracts, and supported integration APIs. Examples should run without access to the source application's infrastructure.

Check that importing a helper has no network side effects or unrelated configuration requirements. For the Metaflow decorator, test local execution separately from Kubernetes configuration. For DAG generation, validate the generated Python and its supported Airflow imports rather than checking only that a file was written.

Choose tests appropriate to the behavior; avoid tests that only repeat implementation details.

## 8. Document the addition and its update impact

Update the README with the capability, usage, dependencies, configuration table, and limitations. Record breaking signature changes and changed environment names.

Consuming projects update intentionally: select a submodule revision, export the toolkit's runtime dependencies with `uv export --no-dev --no-emit-project --no-hashes`, add that temporary export to their project with `uv add -r`, run project checks, and commit the updated submodule reference and dependency files together. See the README for the commands. Do not assume that moving the submodule automatically installs new dependencies.

## Review checklist

- The reusable responsibility and project-owned responsibilities are explicit.
- Application imports, infrastructure values, personal paths, and business-specific defaults are removed.
- Every setting supports an explicit override with documented precedence.
- Shared imports have no cycles or unwanted framework imports.
- The single dependency list resolves on supported Python versions.
- A synthetic example works from a consuming project's submodule layout.
- Relevant edge cases and integration behavior are verified.
- README, configuration examples, and update notes match the implemented behavior.
