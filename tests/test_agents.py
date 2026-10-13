import asyncio
import subprocess
import sys
import unittest

from reusable_helpers.agents.guardrails import (
    GuardrailPipeline,
    GuardrailResult,
    RegexGuardrail,
    RegexRule,
    Severity,
    Violation,
)
from reusable_helpers.agents.memory import InMemoryMemoryProvider, Memory, MemoryRecallRequest


class GuardrailTests(unittest.IsolatedAsyncioTestCase):
    async def test_warning_does_not_hide_later_block(self):
        guardrail = RegexGuardrail(
            [
                RegexRule("warning", "tone", "urgent", "Check tone", Severity.WARNING),
                RegexRule("block", "secret", "secret", "Contains a secret", Severity.BLOCK),
            ]
        )

        result = await guardrail.validate("urgent secret")

        self.assertFalse(result.allowed)
        self.assertEqual(
            [violation.rule_id for violation in result.violations], ["warning", "block"]
        )

    async def test_pipeline_preserves_block_and_collects_later_results(self):
        class FixedGuardrail:
            def __init__(self, result):
                self.result = result
                self.calls = 0

            async def validate(self, text):
                self.calls += 1
                return self.result

        block = FixedGuardrail(GuardrailResult.reject(Violation("safety", "Blocked")))
        warning = FixedGuardrail(GuardrailResult((Violation("tone", "Caution", Severity.WARNING),)))

        stopped = await GuardrailPipeline([block, warning]).validate("text")
        self.assertFalse(stopped.allowed)
        self.assertEqual(warning.calls, 0)

        collected = await GuardrailPipeline([block, warning], stop_on_rejection=False).validate(
            "text"
        )
        self.assertFalse(collected.allowed)
        self.assertEqual(len(collected.violations), 2)
        self.assertEqual(warning.calls, 1)

    def test_reject_requires_blocking_violation(self):
        with self.assertRaisesRegex(ValueError, "blocking violation"):
            GuardrailResult.reject(Violation("tone", "Caution", Severity.WARNING))


class MemoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_filters_all_metadata_keys_before_limit(self):
        provider = InMemoryMemoryProvider(
            {
                "person": [
                    Memory("Wrong topic", {"topic": "contact", "active": True}),
                    Memory("Missing active", {"topic": "reporting"}),
                    Memory("Correct", {"topic": "reporting", "active": True}),
                    Memory("Also correct", {"topic": "reporting", "active": True}),
                ]
            }
        )

        result = await provider.recall(
            MemoryRecallRequest(
                query="reports",
                subject_id="person",
                filters={"topic": "reporting", "active": True},
                limit=1,
            )
        )

        self.assertEqual([memory.text for memory in result], ["Correct"])

    async def test_missing_key_does_not_match_none(self):
        provider = InMemoryMemoryProvider(
            {"person": [Memory("Missing", {}), Memory("Present", {"marker": None})]}
        )

        result = await provider.recall(
            MemoryRecallRequest(query="marker", subject_id="person", filters={"marker": None})
        )

        self.assertEqual([memory.text for memory in result], ["Present"])


class ImportTests(unittest.TestCase):
    def test_memory_import_does_not_load_pydantic_ai(self):
        script = (
            "import sys\n"
            "from reusable_helpers.agents.memory import Memory\n"
            "assert 'pydantic_ai' not in sys.modules\n"
        )
        subprocess.run([sys.executable, "-c", script], check=True)


class BaseAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_and_stream_apply_preprocessors_in_order(self):
        from pydantic_ai import Agent
        from pydantic_ai.messages import (
            ModelMessage,
            ModelRequest,
            ModelResponse,
            TextPart,
            UserPromptPart,
        )
        from pydantic_ai.models.test import TestModel

        from reusable_helpers.agents.base_agent import BaseAgent

        prepared_inputs: list[tuple[str, object, object]] = []

        def first(prompt, history, context):
            return f"{prompt} one"

        async def second(prompt, history, context):
            await asyncio.sleep(0)
            prepared = f"{prompt} two"
            prepared_inputs.append((prepared, history, context))
            return prepared

        underlying = Agent(TestModel(custom_output_text="done"))
        agent = BaseAgent(underlying, preprocessors=[first, second])
        history: list[ModelMessage] = [
            ModelRequest(parts=[UserPromptPart("previous")]),
            ModelResponse(parts=[TextPart("previous reply")]),
        ]
        context = {"id": 1}

        result = await agent.run("input", history=history, context=context)
        self.assertEqual(result.output, "done")
        self.assertTrue(
            any(
                isinstance(part, UserPromptPart) and part.content == "input one two"
                for message in result.all_messages()
                if isinstance(message, ModelRequest)
                for part in message.parts
            )
        )
        async with agent.stream("input", history=history, context=context) as stream_result:
            self.assertEqual(await stream_result.get_output(), "done")

        self.assertEqual(
            prepared_inputs,
            [
                ("input one two", history, context),
                ("input one two", history, context),
            ],
        )
        self.assertFalse(hasattr(agent, "agent"))


if __name__ == "__main__":
    unittest.main()
