from langgraph.graph import END, START, StateGraph

from app.agents.nodes import AgentNodes
from app.agents.state import AgentState
from app.llm.base import BaseLLM


class ChatAgent:

    def __init__(self, llm: BaseLLM):

        nodes = AgentNodes(llm)

        graph = StateGraph(AgentState)

        graph.add_node(
            "generate_response",
            nodes.generate_response,
        )

        graph.add_edge(
            START,
            "generate_response",
        )

        graph.add_edge(
            "generate_response",
            END,
        )

        self.graph = graph.compile()

    async def run(self, message: str) -> str:

        result = await self.graph.ainvoke(
            {
                "message": message,
                "response": "",
            }
        )

        return result["response"]