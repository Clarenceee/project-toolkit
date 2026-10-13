import asyncio
import re

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from reusable_helpers.agents.base_agent import BaseAgent


def trim_input(prompt: str, history: object, context: object) -> str:
    return prompt.strip()


async def main() -> None:
    prepared_inputs: list[str] = []

    def hide_email(prompt: str, history: object, context: object) -> str:
        prepared = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", prompt)
        prepared_inputs.append(prepared)
        return prepared

    agent = BaseAgent(
        Agent(TestModel(custom_output_text="Done.")),
        preprocessors=[trim_input, hide_email],
    )
    result = await agent.run("  Contact alice@example.test  ")

    print(f"Prepared input: {prepared_inputs[0]!r}")
    print(f"Result: {result.output}")


if __name__ == "__main__":
    asyncio.run(main())
