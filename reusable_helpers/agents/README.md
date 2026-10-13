# Agents

The modules in this folder provide prompt loading, input preprocessing, payload redaction, memory, and agent registration. Import each module directly. `BaseAgent` requires the `agents` optional dependency; prompt loading uses PyYAML from the core dependencies. Project-specific models, tools, prompts, and policies belong in the consuming project.

## Load a prompt and run an agent

[`examples/agents/prompt.yaml`](../../examples/agents/prompt.yaml) defines the agent's instructions. [`examples/agents/prompt_agent.py`](../../examples/agents/prompt_agent.py) loads the YAML file, renders `{language}`, and passes the resulting text to a configured Pydantic AI `Agent`. It then wraps that agent with `BaseAgent` to preprocess user input.

Run from the repository root:

```bash
uv run --extra agents python examples/agents/prompt_agent.py
```

Expected output:

```text
Instructions: 'You are a concise assistant. Reply in English.'
Prepared input: 'Say hello'
Result: Hello!
```

The example uses Pydantic AI's `TestModel` for deterministic local output and needs no credentials. Replace it with the consuming project's configured model in an application.

## What a preprocessor does

`BaseAgent` calls each preprocessor before passing a user prompt to the underlying agent. A preprocessor receives the current prompt, message history, and caller context, then returns text. It may be synchronous or asynchronous. With multiple preprocessors, each receives the previous one's output in the order supplied. The same processing runs for `run()` and `stream()`.

In the example, `strip_input` removes surrounding whitespace from `"  Say hello  "`, so the agent receives `"Say hello"`. The rendered YAML prompt is an **instruction** configured on the Pydantic AI agent; preprocessors change the **user input**, not those instructions. `BaseAgent` forwards history as `message_history` and context as `deps`. A preprocessor that returns a non-string value raises `TypeError`.

Use preprocessors when every run should apply the same prompt transformation before the model sees it. The [preprocessor example](../../examples/agents/preprocessors.py) runs two in order: it trims whitespace, then replaces an email address. Run it from the repository root:

```bash
uv run --extra agents python examples/agents/preprocessors.py
```

Expected output:

```text
Prepared input: 'Contact [EMAIL]'
Result: Done.
```

The example records the final input to show the transformation. In an application, the preprocessor only needs to return the transformed text.

## Redact a payload

Use `PayloadRedactor` when a nested dictionary, list, tuple, or string needs caller-defined fields and text patterns replaced before it is passed elsewhere. Field rules match keys, while text rules replace matches inside string values. `redact()` returns a new value and a replacement count; it does not modify the original payload. The [payload example](../../examples/agents/payload_redaction.py) uses synthetic data:

```bash
uv run python examples/agents/payload_redaction.py
```

Expected output:

```text
{'customer': {'email': '[EMAIL]', 'api_key': '[REDACTED]'}, 'messages': ['Email [EMAIL]'], 'active': True}
Replacements: 3
```

The example replaces `api_key` by field name and email addresses by regex. Each project supplies its own sensitive fields and patterns. A prompt preprocessor can call `PayloadRedactor.redact(prompt).value` when it needs the same text rule before an agent run.

## Choose an agent by name

Use `AgentRegistry` when an application has multiple named agent builders and chooses one at runtime. Register an `AgentSpec` for each name, then call `registry.build(name, **dependencies)`. The registry passes dependencies to the selected builder; it does not create models or clients itself. Duplicate names and unknown names raise clear errors. The [registry example](../../examples/agents/agent_registry.py) registers support and summary agents:

```bash
uv run --extra agents python examples/agents/agent_registry.py
```

Expected output:

```text
Available agents: ('summary', 'support')
Result: Support ready.
```

The agent examples use Pydantic AI's `TestModel` for deterministic output and need no credentials. Pass the application's configured model to `registry.build()` in production.

For input checks and moderation, see the [guardrails README](guardrails/README.md).
