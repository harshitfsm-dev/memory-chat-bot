"""Short-term memory: turning saved messages back into a prompt.

Everything here is a plain function with no database and no model calls, so it
is easy to read and easy to test.

The idea in one sentence: to answer a new message, send the model a short
summary of the old messages plus the most recent messages word for word.
"""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.models.chat_message import ROLE_USER, ChatMessage

SUMMARY_PREFIX = "Summary of earlier messages in this conversation:\n"


def build_prompt(
    history: list[ChatMessage],
    new_message: str,
    summary: str | None = None,
) -> list[BaseMessage]:
    """Build the message list to send the model.

    Order matters, so it goes: summary first (if there is one), then the older
    messages, then the new message last.

    `history` must already exclude anything the summary covers, otherwise the
    model sees the same exchange twice.
    """
    messages: list[BaseMessage] = []

    if summary and summary.strip():
        messages.append(SystemMessage(content=SUMMARY_PREFIX + summary.strip()))

    for message in history:
        if message.role == ROLE_USER:
            messages.append(HumanMessage(content=message.content))
        else:
            messages.append(AIMessage(content=message.content))

    messages.append(HumanMessage(content=new_message))
    return messages


def render_for_summary(messages: list[ChatMessage]) -> str:
    """Format messages as plain text for the summarizing model to read."""
    lines = []
    for message in messages:
        speaker = "User" if message.role == ROLE_USER else "Assistant"
        lines.append(f"{speaker}: {message.content.strip()}")
    return "\n".join(lines)
