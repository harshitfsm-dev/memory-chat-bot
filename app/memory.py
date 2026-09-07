"""Short-term memory: turning saved messages back into a prompt.

Everything here is a plain function with no database and no model calls, so it
is easy to read and easy to test.

The idea in one sentence: to answer a new message, send the model a short
summary of the old messages plus the most recent messages word for word.

Sizes are measured in **tokens**, not messages. Counting messages looks simpler
but breaks badly: twenty short messages fit easily while twenty long ones can be
twenty times the model's whole context window.
"""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.messages.utils import count_tokens_approximately

from app.models.chat_message import ROLE_USER, ChatMessage

SUMMARY_PREFIX = "Summary of our earlier conversation:\n"

# What the assistant "replies" to the summary, to close the priming exchange.
SUMMARY_ACK = "Understood, I have that context."


def count_tokens(messages: list[BaseMessage]) -> int:
    """Roughly how many tokens these messages cost.

    Uses LangChain's estimate rather than the model's real tokenizer, because
    Ollama does not expose one. It is close enough for budgeting as long as the
    budget leaves some slack, which is why the settings do.
    """
    return count_tokens_approximately(messages)


def to_langchain(messages: list[ChatMessage]) -> list[BaseMessage]:
    """Convert saved rows into the message objects the model expects."""
    converted: list[BaseMessage] = []
    for message in messages:
        if message.role == ROLE_USER:
            converted.append(HumanMessage(content=message.content))
        else:
            converted.append(AIMessage(content=message.content))
    return converted


def start_at_user_message(messages: list[ChatMessage]) -> list[ChatMessage]:
    """Drop leading assistant messages so the history starts with a question.

    A window that opens on an assistant reply shows the model an answer with no
    question before it. In testing that was enough to make the model deny facts
    it had actually been told — it could not tell which side had said what.

    This happens whenever a cut lands between a user message and its reply, so
    both the token budget and the summary boundary need to respect it.
    """
    first_user = next(
        (i for i, m in enumerate(messages) if m.role == ROLE_USER),
        len(messages),
    )
    return messages[first_user:]


def fit_to_budget(
    messages: list[ChatMessage],
    budget_tokens: int,
) -> list[ChatMessage]:
    """Keep the newest messages that fit in `budget_tokens`, oldest first.

    Walks from the newest backwards, because recent messages matter most, and
    stops as soon as adding one more would go over. The result always begins
    with a user message.

    Whatever this drops is history the model will not see, so callers should
    notice when it drops anything: it means summarizing has not kept up.
    """
    kept: list[ChatMessage] = []
    used = 0

    for message in reversed(messages):
        cost = count_tokens(to_langchain([message]))
        if used + cost > budget_tokens:
            break
        kept.append(message)
        used += cost

    kept.reverse()
    return start_at_user_message(kept)


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

    The summary is delivered as a user message plus a short assistant
    acknowledgement, rather than as a SystemMessage. That looks roundabout but a
    SystemMessage here was measurably broken: with tools bound, the chat template
    fills the system slot with tool definitions, and a second system message was
    quietly ignored. The model then denied facts it had been given. The same test
    passed with this priming pair, so the summary now travels as ordinary
    conversation, which every chat template handles the same way.
    """
    messages: list[BaseMessage] = []

    if summary and summary.strip():
        messages.append(HumanMessage(content=SUMMARY_PREFIX + summary.strip()))
        messages.append(AIMessage(content=SUMMARY_ACK))

    messages.extend(to_langchain(history))
    messages.append(HumanMessage(content=new_message))
    return messages


def render_for_summary(messages: list[ChatMessage]) -> str:
    """Format messages as plain text for the summarizing model to read."""
    lines = []
    for message in messages:
        speaker = "User" if message.role == ROLE_USER else "Assistant"
        lines.append(f"{speaker}: {message.content.strip()}")
    return "\n".join(lines)
