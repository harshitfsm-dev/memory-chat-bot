from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallResult,
    ModelRequest,
    ModelResponse,
    ToolErrorMiddleware,
    ToolRetryMiddleware,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import trim_messages
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from app.agents.tools import AGENT_TOOLS, handle_tool_error


SYSTEM_PROMPT = """You are a concise, helpful assistant.
Use a provided tool whenever it can answer the user's request more reliably.
Do not claim that a tool ran unless you received its result.
If a tool fails, explain that you could not complete that part of the request.
"""


class TrimHistoryMiddleware(AgentMiddleware):
    """Cap the history sent to the model without discarding checkpointed state."""

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


retry_middleware = ToolRetryMiddleware(
    max_retries=5,
    retry_on=lambda e: True,  # Transient exceptions to intercept
    on_failure="continue",  # Sends the error back to the LLM as an observation
    initial_delay=0.5,
    backoff_factor=0.0,  # Constant delay instead of exponential
    jitter=False,
)


def build_agent(
    model: BaseChatModel,
    checkpointer: BaseCheckpointSaver,
    history_max_tokens: int,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Create the single-agent chat runtime.

    A chatbot only needs one model/tool loop, so `create_agent` replaces the
    hand-rolled `StateGraph`: same ReAct behaviour, less wiring to maintain.
    """
    return create_agent(
        model=model,
        tools=AGENT_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        middleware=[
            # TrimHistoryMiddleware(history_max_tokens),
            ToolErrorMiddleware(on_error=handle_tool_error),
            retry_middleware,
        ],
        checkpointer=checkpointer,
    )
