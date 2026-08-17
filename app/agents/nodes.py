from app.agents.state import AgentState
from app.llm.base import BaseLLM


class AgentNodes:

    def __init__(self, llm: BaseLLM):
        self.llm = llm

    async def generate_response(
        self,
        state: AgentState,
    ) -> AgentState:

        response = await self.llm.generate(
            state["message"]
        )

        return {
            **state,
            "response": response,
        }