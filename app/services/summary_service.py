import asyncio
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph

from app.db.unit_of_work import UnitOfWork
from app.memory import count_tokens, render_for_summary, to_langchain
from app.models.chat_message import ROLE_USER, ChatMessage
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_thread_repository import ChatThreadRepository

logger = logging.getLogger(__name__)


class SummaryService:
    """Replaces a thread's older messages with a short summary.

    Without this, a long conversation eventually has more messages than we can
    send the model, and the oldest ones are simply forgotten. Summarizing keeps
    the gist of them in a few lines instead.

    How it decides, all in tokens rather than message counts:
      * Add up the tokens the summary does not cover yet.
      * If that is under `trigger_tokens`, do nothing.
      * Otherwise summarize the oldest of them, keeping the newest
        `keep_recent_tokens` word for word because follow-up questions refer to
        them ("that one", "make it 5 instead").

    Tokens matter here rather than message counts because a handful of pasted
    documents can be larger than a hundred short replies. Counting messages
    would let a thread blow past the prompt budget without ever triggering.
    """

    def __init__(
        self,
        chat_message_repo: ChatMessageRepository,
        chat_thread_repo: ChatThreadRepository,
        uow: UnitOfWork,
        summary_agent: CompiledStateGraph[Any, Any, Any, Any],
        agent_semaphore: asyncio.Semaphore,
        *,
        enabled: bool,
        trigger_tokens: int,
        keep_recent_tokens: int,
        max_messages_per_run: int,
        timeout_seconds: float,
    ):
        self.chat_message_repo = chat_message_repo
        self.chat_thread_repo = chat_thread_repo
        self.uow = uow
        self.summary_agent = summary_agent
        self.agent_semaphore = agent_semaphore
        self.enabled = enabled
        self.trigger_tokens = trigger_tokens
        self.keep_recent_tokens = keep_recent_tokens
        self.max_messages_per_run = max_messages_per_run
        self.timeout_seconds = timeout_seconds

    async def update_if_needed(
        self,
        thread_id: str,
        current_summary: str | None,
        summary_up_to_seq: int,
    ) -> bool:
        """Summarize the thread's older messages if it has grown enough.

        Returns True if a new summary was saved.

        Called after a chat turn has already been saved, so failing here is not
        a problem: nothing is lost, and the next turn will try again.
        """
        if not self.enabled:
            return False

        pending = await self.chat_message_repo.get_recent_messages(
            thread_id=thread_id,
            limit=self.max_messages_per_run,
            after_seq=summary_up_to_seq,
        )
        if count_tokens(to_langchain(pending)) < self.trigger_tokens:
            return False

        to_summarize = self._pick_messages_to_summarize(pending)
        if not to_summarize:
            return False

        through_seq = to_summarize[-1].seq
        transcript = render_for_summary(to_summarize)

        # This waits on the model while the database transaction stays open,
        # which holds a connection for a few seconds. Fine at this scale; a
        # busier app would run summarizing outside the request instead.
        summary = await self._write_summary(current_summary, transcript)
        if summary is None:
            # Nothing usable came back. Leave the old summary and boundary alone
            # so the same messages are tried again after the next turn.
            logger.warning("Summarizer returned nothing for thread=%s", thread_id)
            return False

        await self.chat_thread_repo.save_summary(
            thread_id=thread_id,
            summary=summary,
            up_to_seq=through_seq,
        )
        await self.uow.commit()

        logger.info(
            "Summary updated: thread=%s up_to_seq=%s messages_summarized=%s "
            "tokens_replaced=%s summary_tokens=%s",
            thread_id,
            through_seq,
            len(to_summarize),
            count_tokens(to_langchain(to_summarize)),
            count_tokens([HumanMessage(content=summary)]),
        )
        return True

    def _pick_messages_to_summarize(
        self,
        pending: list[ChatMessage],
    ) -> list[ChatMessage]:
        """Choose the oldest messages to fold into the summary.

        Works backwards from the newest, holding back `keep_recent_tokens` worth
        of messages to stay word for word. Everything older than that gets
        summarized.

        The cut is then moved forward until the next message is a user message,
        so the summary always ends where an exchange ended. Cutting between a
        question and its answer would leave the answer stranded at the start of
        the replayed window, and a model shown a reply with no question misreads
        who said what.

        Returns an empty list when the newest messages already fill the
        keep-recent allowance — nothing is old enough to summarize yet.
        """
        keep_from = len(pending)
        kept_tokens = 0

        for index in range(len(pending) - 1, -1, -1):
            cost = count_tokens(to_langchain([pending[index]]))
            if kept_tokens + cost > self.keep_recent_tokens:
                break
            kept_tokens += cost
            keep_from = index

        # Move forward to the next question. Forward rather than back, because
        # moving back would often land on 0 and summarize nothing at all when
        # one very large message sits at the start.
        while keep_from < len(pending) and pending[keep_from].role != ROLE_USER:
            keep_from += 1

        return pending[:keep_from]

    async def _write_summary(
        self,
        current_summary: str | None,
        transcript: str,
    ) -> str | None:
        """Ask the model to fold new messages into the existing notes.

        Returns None if the model gave us nothing usable, which happens
        occasionally and is not worth failing over.

        The model only ever sees the old notes plus what is new, never the whole
        conversation, so this prompt stays small however long the thread gets.
        """
        notes = current_summary.strip() if current_summary else "(none yet)"
        prompt = f"Notes so far:\n{notes}\n\nNewer messages:\n{transcript}"

        # Shares the chat concurrency limit so summarizing cannot slow down
        # someone waiting for an answer.
        async with asyncio.timeout(self.timeout_seconds):
            async with self.agent_semaphore:
                result = await self.summary_agent.ainvoke(
                    {"messages": [HumanMessage(content=prompt)]},
                )

        messages = result.get("messages", [])
        if not messages or not isinstance(messages[-1], AIMessage):
            return None

        return messages[-1].text.strip() or None
