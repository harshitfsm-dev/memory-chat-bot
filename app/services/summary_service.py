import asyncio
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph

from app.db.unit_of_work import UnitOfWork
from app.memory import render_for_summary
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_thread_repository import ChatThreadRepository

logger = logging.getLogger(__name__)


class SummaryService:
    """Replaces a thread's older messages with a short summary.

    Without this, a long conversation eventually has more messages than we can
    send the model, and the oldest ones are simply forgotten. Summarizing keeps
    the gist of them in a few lines instead.

    How it decides:
      * Count the messages the summary does not cover yet.
      * If that is under `trigger_messages`, do nothing.
      * Otherwise summarize all of them except the newest `keep_recent_messages`,
        which stay word for word because follow-up questions refer to them
        ("that one", "make it 5 instead").
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
        trigger_messages: int,
        keep_recent_messages: int,
        timeout_seconds: float,
    ):
        self.chat_message_repo = chat_message_repo
        self.chat_thread_repo = chat_thread_repo
        self.uow = uow
        self.summary_agent = summary_agent
        self.agent_semaphore = agent_semaphore
        self.enabled = enabled
        self.trigger_messages = trigger_messages
        self.keep_recent_messages = keep_recent_messages
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

        pending = await self.chat_message_repo.count_after(
            thread_id=thread_id,
            after_seq=summary_up_to_seq,
        )
        if pending < self.trigger_messages:
            return False

        # Summarize everything except the newest few messages.
        through_seq = summary_up_to_seq + (pending - self.keep_recent_messages)
        if through_seq <= summary_up_to_seq:
            return False

        messages = await self.chat_message_repo.get_messages_in_range(
            thread_id=thread_id,
            after_seq=summary_up_to_seq,
            through_seq=through_seq,
        )
        if not messages:
            return False

        transcript = render_for_summary(messages)

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
            "Summary updated: thread=%s up_to_seq=%s messages_summarized=%s",
            thread_id,
            through_seq,
            len(messages),
        )
        return True

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
