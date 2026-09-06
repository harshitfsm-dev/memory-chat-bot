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

from app.agents.tools import AGENT_TOOLS, handle_tool_error


SYSTEM_PROMPT = """You are a concise, helpful assistant.
Use a provided tool whenever it can answer the user's request more reliably.
Do not claim that a tool ran unless you received its result.
If a tool fails, explain that you could not complete that part of the request.
"""

TITLE_PROMPT = """You name chat conversations.
Summarise the user's message as a title of at most six words.
Reply with the title only: no quotes, no prefix, no trailing punctuation.
Never answer the message itself.
"""

SUMMARY_PROMPT = """You keep short notes about a conversation.

You are given the notes so far (possibly empty) and the messages that came
after them. Rewrite the notes so they cover both.

Always keep:
- Facts the user stated about themselves or their situation.
- Exact names, numbers, codes and dates, copied character for character.
- Decisions made, and questions the user asked that were never answered.

Rules:
- Write short third-person notes, one fact per line. Not dialogue, not prose.
- Never shorten or reword an identifier. A wrong number is worse than no number.
- If the notes and a newer message disagree, the newer message is correct.
- Reply with the notes only. Never answer or continue the conversation.
"""


class TrimHistoryMiddleware(AgentMiddleware):
    """Cap messages sent to the model during a single agent run."""

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
