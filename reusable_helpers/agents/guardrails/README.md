# Guardrail pipeline

`GuardrailPipeline` runs guardrails in order. Each guardrail receives the text returned as `sanitized_text` by the previous one. Warnings are reported but allow the text; a `BLOCK` violation rejects it. The pipeline stops after a rejection by default.

## Runnable example

Save this as `guardrail_example.py` and run `python guardrail_example.py` from the repository root:

```python
import asyncio

from reusable_helpers.agents.guardrails import (
    GuardrailPipeline,
    GuardrailResult,
    RegexGuardrail,
    RegexRule,
    Severity,
)


class TrimWhitespace:
    async def validate(self, text: str) -> GuardrailResult:
        return GuardrailResult.allow(sanitized_text=text.strip())


async def main() -> None:
    pipeline = GuardrailPipeline(
        [
            TrimWhitespace(),
            RegexGuardrail(
                [
                    RegexRule("urgent", "tone", r"\burgent\b", "Check urgency", Severity.WARNING),
                    RegexRule("secret", "privacy", r"\bsecret\b", "Contains a secret"),
                ]
            ),
        ]
    )

    for text in (" hello ", " urgent ", " urgent secret "):
        result = await pipeline.validate(text)
        checked_text = result.sanitized_text if result.sanitized_text is not None else text
        print(result.allowed, repr(checked_text), [v.rule_id for v in result.violations])


asyncio.run(main())
```

Expected output:

```text
True 'hello' []
True 'urgent' ['urgent']
False 'urgent secret' ['urgent', 'secret']
```

The regex guardrail continues past a warning to find a later blocking rule. Set `collect_all=True` on `RegexGuardrail` to collect matches after the first block. Set `stop_on_rejection=False` on `GuardrailPipeline` to run later guardrails even after a block; the final result remains rejected.

## Adding moderation

`ModerationGuardrail` is one check: it asks an injected provider to classify text and returns a blocking violation when the provider flags it. If the provider raises an error, it blocks by default (`fail_closed=True`). Set `fail_closed=False` only when the application should allow text during a provider failure.

`GuardrailPipeline` runs checks in order. It passes sanitized text to the next check, collects violations, and stops after a rejection by default. Add moderation to a pipeline alongside regex or other checks when you need more than one mechanism. The provider implements `async check(text)` and returns a `ModerationDecision`:

```python
from reusable_helpers.agents.guardrails import (
    GuardrailPipeline,
    ModerationDecision,
    ModerationGuardrail,
)


class ExampleProvider:
    async def check(self, text: str) -> ModerationDecision:
        return ModerationDecision(flagged="unsafe" in text)


pipeline = GuardrailPipeline([ModerationGuardrail(ExampleProvider())])
```

You can also call `ModerationGuardrail.validate(text)` directly when moderation is the only check. Replace `ExampleProvider` with a project-owned provider. The package also includes `OpenAIModerationProvider`, which accepts an injected AsyncOpenAI-compatible client. The pipeline returns violation data; the calling application chooses any user-facing response.
