from collections.abc import Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, trim_messages
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.tools import AGENT_TOOLS, handle_tool_error


SYSTEM_PROMPT = """You are a concise, helpful assistant.
Use a provided tool whenever it can answer the user's request more reliably.
Do not claim that a tool ran unless you received its result.
If a tool fails, explain that you could not complete that part of the request.
"""


class AgentWorkflow:
    def __init__(
        self,
        model: BaseChatModel,
        tools: Sequence[BaseTool],
        history_max_tokens: int,
    ):
        self.model = model.bind_tools(tools)
        self.history_max_tokens = history_max_tokens
        self.tool_node = ToolNode(
            tools,
            handle_tool_errors=handle_tool_error,
        )

    async def call_model(self, state: MessagesState) -> dict[str, list[BaseMessage]]:
        history = trim_messages(
            state["messages"],
            max_tokens=self.history_max_tokens,
            token_counter="approximate",
            strategy="last",
            start_on="human",
            end_on=("human", "tool"),
            include_system=False,
        )
        response = await self.model.ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT), *history]
        )
        return {"messages": [response]}

    def compile(
        self,
        checkpointer: BaseCheckpointSaver,
    ) -> CompiledStateGraph:
        graph = StateGraph(MessagesState)
        graph.add_node("agent", self.call_model)
        graph.add_node("tools", self.tool_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges(
            "agent",
            tools_condition,
            {"tools": "tools", "__end__": END},
        )
        graph.add_edge("tools", "agent")
        return graph.compile(checkpointer=checkpointer)


def build_agent_graph(
    model: BaseChatModel,
    checkpointer: BaseCheckpointSaver,
    history_max_tokens: int,
) -> CompiledStateGraph:
    return AgentWorkflow(
        model=model,
        tools=AGENT_TOOLS,
        history_max_tokens=history_max_tokens,
    ).compile(checkpointer)
