from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallResult,
    ModelRequest,
    ModelResponse,
    ToolErrorMiddleware,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import trim_messages
from langgraph.graph.state import CompiledStateGraph

from app.agents.prompts import SUMMARY_PROMPT, SYSTEM_PROMPT, TITLE_PROMPT
from app.agents.tools import AGENT_TOOLS, handle_tool_error


class TrimHistoryMiddleware(AgentMiddleware):
    """Last-resort cap on messages sent to the model during a single run.

    ChatService already fits the prompt to the same token budget before the run
    starts, so this normally does nothing. It exists for growth *inside* a run,
    where each tool call and result is appended and the model is called again.

    It trims from the oldest end, which is where the thread summary sits. That is
    acceptable for a backstop: if this fires the prompt was already in trouble.
    """

    def __init__(self, max_tokens: int):
        super().__init__()
        self.max_tokens = max_tokens

    def _trim(self, request: ModelRequest) -> ModelRequest:
        return request.override(
            messages=trim_messages(
                request.messages,
                max_tokens=self.max_tokens,
                token_counter="approximate",
                strategy="last",
                start_on="human",
                end_on=("human", "tool"),
                include_system=False,
            )
        )

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelCallResult:
        return handler(self._trim(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        return await handler(self._trim(request))


def build_agent(
    model: BaseChatModel,
    history_max_tokens: int,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Create the stateless model/tool loop used for chat responses."""
    return create_agent(
        model=model,
        tools=AGENT_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        middleware=[
            TrimHistoryMiddleware(history_max_tokens),
            ToolErrorMiddleware(on_error=handle_tool_error),
        ],
    )


def build_title_agent(
    model: BaseChatModel,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Create the lightweight runtime for short, one-shot side tasks."""
    return create_agent(
        model=model,
        system_prompt=TITLE_PROMPT,
    )


def build_summary_agent(
    model: BaseChatModel,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Create the runtime that writes a thread's summary.

    No tools and no history trimming: the input is one prompt we already keep
    small, and trimming it would throw away the messages we are trying to
    summarize.
    """
    return create_agent(
        model=model,
        system_prompt=SUMMARY_PROMPT,
    )
