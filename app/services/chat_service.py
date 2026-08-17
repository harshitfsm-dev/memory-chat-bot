import asyncio
import logging

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph


logger = logging.getLogger(__name__)


class AgentExecutionError(RuntimeError):
    """Raised when the agent cannot produce a safe final response."""


class ChatService:
    def __init__(
        self,
        graph: CompiledStateGraph,
        *,
        timeout_seconds: float,
        recursion_limit: int,
    ):
        self.graph = graph
        self.timeout_seconds = timeout_seconds
        self.recursion_limit = recursion_limit

    async def chat(self, message: str, user_id: str) -> str:
        # Keep one checkpointed conversation per authenticated user.
        config: RunnableConfig = {
            "configurable": {"thread_id": f"user:{user_id}:chat"},
            "recursion_limit": self.recursion_limit,
        }

        try:
            async with asyncio.timeout(self.timeout_seconds):
                result = await self.graph.ainvoke(
                    {"messages": [HumanMessage(content=message)]},
                    config=config,
                )
            return self._final_answer(result)
        except Exception as exc:
            logger.exception("Agent execution failed for user %s", user_id)
            raise AgentExecutionError("Agent execution failed") from exc

    @staticmethod
    def _final_answer(result: dict) -> str:
        messages = result.get("messages", [])
        if not messages or not isinstance(messages[-1], AIMessage):
            raise AgentExecutionError("Agent returned no final message")

        answer = messages[-1].text
        if not answer.strip():
            raise AgentExecutionError("Agent returned no answer text")
        return answer
