import asyncio

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from reusable_helpers.agents.agent_registry import AgentRegistry, AgentSpec
from reusable_helpers.agents.base_agent import BaseAgent


def build_support_agent(*, model: TestModel) -> BaseAgent:
    return BaseAgent(Agent(model, instructions="Answer support questions concisely."))


def build_summary_agent(*, model: TestModel) -> BaseAgent:
    return BaseAgent(Agent(model, instructions="Summarize the supplied text concisely."))


async def main() -> None:
    registry: AgentRegistry[BaseAgent] = AgentRegistry()
    registry.register(AgentSpec(name="support", builder=build_support_agent))
    registry.register(AgentSpec(name="summary", builder=build_summary_agent))

    print(f"Available agents: {registry.names()}")
    agent = registry.build("support", model=TestModel(custom_output_text="Support ready."))
    result = await agent.run("How can I get help?")
    print(f"Result: {result.output}")


if __name__ == "__main__":
    asyncio.run(main())
