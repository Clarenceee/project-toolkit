import asyncio
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from reusable_helpers.agents.base_agent import BaseAgent
from reusable_helpers.agents.prompt_loader import load_prompt


def strip_input(prompt: str, history: object, context: object) -> str:
    return prompt.strip()


async def main() -> None:
    template = load_prompt(Path(__file__).with_name("prompt.yaml"))
    instructions = template.render(variables={"language": "English"})
    prepared_inputs: list[str] = []

    def prepare(prompt: str, history: object, context: object) -> str:
        prepared = strip_input(prompt, history, context)
        prepared_inputs.append(prepared)
        return prepared

    agent = BaseAgent(
        Agent(TestModel(custom_output_text="Hello!"), instructions=instructions),
        preprocessors=[prepare],
    )
    result = await agent.run("  Say hello  ")

    print(f"Instructions: {instructions!r}")
    print(f"Prepared input: {prepared_inputs[0]!r}")
    print(f"Result: {result.output}")


if __name__ == "__main__":
    asyncio.run(main())
