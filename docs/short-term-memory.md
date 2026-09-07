# Short-term memory, end to end

How this app makes the model remember a conversation.

The agent itself remembers nothing. Every request rebuilds the conversation from
the database, sends it to the model, and throws it away. That sounds wasteful but
it has one big advantage: **whatever the model saw, you can reconstruct from
SQL.** There is no hidden state to guess at.

---

## The idea in one sentence

To answer a new message, send the model a short summary of the old messages plus
the most recent messages word for word.

```
┌──────────────────────────────────────────────┐
│ "Summary of our earlier conversation: ..."    │  <- old messages, compressed
│ "Understood, I have that context."            │
├──────────────────────────────────────────────┤
│ User:      "and what about Bolt?"             │  <- recent messages, verbatim
│ Assistant: "Bolt is your dog."                │
├──────────────────────────────────────────────┤
│ User:      "how old is Pixel?"                │  <- the new message
└──────────────────────────────────────────────┘
```

Everything is measured in **tokens**, never in message counts. Twenty one-line
messages and twenty pasted documents are both "twenty messages" but one fits
easily and the other is many times the model's whole capacity.

---

## The two columns that make it work

Only two database columns exist for memory.

**`chat_messages.seq`** — the position of a message inside its thread: 1, 2,
3... We order by this rather than `created_at` because messages saved in the same
transaction share a timestamp, which leaves their order undefined.

**`chat_threads.summary_up_to_seq`** — how far the thread's summary reaches. `0`
means nothing has been summarized yet.

Together they split every thread in two:

```
seq:  1    2    3    4    5    6    7    8
      └──────────────┘    └──────────────┘
      summary covers      replayed word for word
      (summary_up_to_seq = 4)
```

The replay window only loads messages with a **higher** `seq` than the boundary.
That is what stops the same exchange appearing twice — once paraphrased in the
summary and once verbatim.

The summary text itself lives in `chat_threads.summary`.

---

## The files

| File | Responsibility |
| --- | --- |
| `app/memory.py` | Plain functions. Rows in, messages out. No database, no model calls. |
| `app/services/chat_service.py` | Orchestrates a turn: load memory, call the model, save, refresh the summary. |
| `app/services/summary_service.py` | Decides when to summarize and writes the summary. |
| `app/repositories/chat_message_repository.py` | The SQL for reading and appending messages. |
| `app/core/config.py` | The token budgets, and the startup checks on them. |

`app/memory.py` is the one to read first. It has no I/O, so you can follow it
top to bottom without thinking about async or databases.

---

## Walking through one request

Say a user posts `POST /chat/` with `{"message": "how old is Pixel?",
"thread_id": "abc"}`.

### Step 1 — resolve the thread

`ChatService.chat()` (`chat_service.py:105`) calls `_resolve_thread`, which
proves the thread belongs to this user. A request with someone else's `thread_id`
gets a 404 here, before anything is read.

### Step 2 — build the prompt

`_build_prompt` (`chat_service.py:311`) is where memory actually happens.

First it works out what it *cannot* drop — the summary and the new message:

```python
required = build_prompt([], message, thread.summary)
required_tokens = count_tokens(required)
if required_tokens > self.history_max_tokens:
    raise MessageTooLongError(...)
```

If the new message alone will not fit, that is an error, not something to paper
over. The caller gets a **413**. (Before this check existed, an oversized message
made the trim middleware return an empty list, the agent then looped until it hit
the recursion limit, and the caller got a confusing 502.)

Then it loads recent messages, skipping anything the summary already covers:

```python
history = await self.chat_message_repo.get_recent_messages(
    thread_id=thread.id,
    limit=self.history_max_messages,      # row cap, so the query stays small
    after_seq=thread.summary_up_to_seq,   # skip what the summary covers
)
```

Then it keeps as many as fit the leftover budget:

```python
kept = fit_to_budget(history, self.history_max_tokens - required_tokens)
```

`fit_to_budget` (`memory.py`) walks from the newest message backwards, adding
messages until the next one would go over budget. Newest-first because recent
messages matter most.

If anything gets dropped, that is logged as a warning:

```
Dropped 3 unsummarized message(s) for space: thread=abc summary_up_to_seq=4
```

That line means trouble. Those messages are not in the summary and not in the
prompt, so they are simply forgotten. It means summarizing is not keeping pace,
and the fix is to lower `SUMMARY_TRIGGER_TOKENS` or raise
`AGENT_HISTORY_MAX_TOKENS`.

Finally `build_prompt` assembles the list: summary, then history, then the new
message.

### Step 3 — save the user's message

`_save_message` (`chat_service.py:362`) gets the next position and appends:

```python
seq = await self.chat_message_repo.next_seq(thread_id)   # MAX(seq) + 1
self.chat_message_repo.create(thread_id, role, content, seq=seq)
await self.uow.commit()
```

This commits **before** the model call, on purpose. Committing releases the
pooled database connection, so no connection is held during the slow model call.
It also means the user's message survives even if generation then fails.

### Step 4 — call the model

```python
result = await self.agent.ainvoke({"messages": messages}, config=config)
```

The messages we just built are the entire memory. The agent has no checkpointer,
so nothing carries over from the last request.

### Step 5 — save the answer, then refresh the summary

`_save_message` again for the assistant's reply, then `_update_summary`
(`chat_service.py:373`):

```python
try:
    await self.summary_service.update_if_needed(...)
except Exception:
    logger.warning("Could not update summary for thread=%s", ...)
```

Wrapped in `try/except` deliberately. The answer has already been sent and saved,
so a summarizer failure must not turn into a failed request. It is logged, and
the next turn tries again.

The streaming endpoint (`stream_chat`, `chat_service.py:197`) does exactly the
same things in the same order. It calls `_update_summary` *after* the final
`done` chunk, so the client is not kept waiting.

---

## Walking through summarization

`SummaryService.update_if_needed` (`summary_service.py:61`).

### Does it need to run?

```python
pending = await self.chat_message_repo.get_recent_messages(
    thread_id=thread_id, limit=..., after_seq=summary_up_to_seq,
)
if count_tokens(to_langchain(pending)) < self.trigger_tokens:
    return False
```

Load the messages the summary does not cover, add up their tokens, and stop if
they are under `SUMMARY_TRIGGER_TOKENS`.

### Where to cut?

`_pick_messages_to_summarize` (`summary_service.py:120`) walks backwards from the
newest message, holding back `SUMMARY_KEEP_RECENT_TOKENS` worth to stay verbatim.
Everything older gets summarized.

Recent messages stay word for word because follow-up questions point at them —
"that one", "make it 5 instead" — and those references stop making sense once
reworded.

Then one more rule, which matters more than it looks:

```python
# Move forward to the next question.
while keep_from < len(pending) and pending[keep_from].role != ROLE_USER:
    keep_from += 1
```

The cut must land immediately **before a user message**. If it lands between a
question and its answer, the replay window opens on an assistant reply with no
question in front of it — and a model shown an answer out of nowhere cannot tell
which side said what. In testing that alone was enough to make it deny a fact it
had just been given. `memory.start_at_user_message()` guards the same thing on
the budget side.

### Write the summary

`_write_summary` (`summary_service.py:157`) sends the previous notes plus only
the new messages:

```
Notes so far:
User: budget is 4500 EUR for the EU rollout.

Newer messages:
User: actually make that 5000 EUR.
Assistant: Updated to 5000 EUR.
```

This is **incremental** — the model never sees the whole thread, only the notes
plus what changed. That keeps this call's own prompt small no matter how long the
conversation runs.

The prompt (`SUMMARY_PROMPT` in `app/agents/agent.py`) requires every line to
start with `User:` or `Assistant:`. Attribution is not cosmetic: an earlier
version produced neutral notes like "the quarterly report states revenue of 4.2
million EUR", and when the user asked "what figure did I give you?" the model
answered "you didn't" — correctly, because the notes never said who supplied it.

If the model returns nothing usable, `_write_summary` returns `None`, the
boundary is left untouched, and the same messages are retried next turn. Better
than overwriting good notes with junk.

### Save it

```python
await self.chat_thread_repo.save_summary(thread_id, summary, up_to_seq=through_seq)
await self.uow.commit()
```

Text and boundary are written together. A summary without its boundary would
leave us unable to tell which messages it already describes.

Success looks like this in the logs:

```
Summary updated: thread=abc up_to_seq=2 messages_summarized=2
                 tokens_replaced=4783 summary_tokens=20
```

4,783 tokens of conversation became 20. That is the whole point.

---

## A worked example

`AGENT_HISTORY_MAX_TOKENS=10000`, `SUMMARY_TRIGGER_TOKENS=4000`,
`SUMMARY_KEEP_RECENT_TOKENS=1500`.

| Turn | rows | unsummarized tokens | what happens |
| --- | --- | --- | --- |
| 1 | 2 | 300 | under the trigger, nothing to do |
| 2 | 4 | 900 | still under |
| 3 | 6 | 2,100 | still under |
| 4 | 8 | 4,300 | **over 4,000** — summarize the oldest, keep ~1,500 verbatim |
| | | | boundary moves to `seq 4`, summary written |
| 5 | 10 | 1,900 | pending dropped because the summary absorbed the rest |

A single long paste can trigger it on turn 1. In a real test, one 19,000
character message (~4,750 tokens) crossed the trigger immediately, was summarized
into 20 tokens, and the figure inside it was still recalled correctly three turns
later.

---

## Settings, and how they relate

| Setting | Default | Meaning |
| --- | --- | --- |
| `OLLAMA_NUM_CTX` | 16384 | Total tokens the model can read at once. |
| `AGENT_MAX_OUTPUT_TOKENS` | 4096 | Reserved for the reply. |
| `AGENT_HISTORY_MAX_TOKENS` | 10000 | Budget for the whole prompt. **The main dial.** |
| `AGENT_HISTORY_MAX_MESSAGES` | 40 | Row cap on the query only, not the real limit. |
| `SUMMARY_ENABLED` | true | Off means old messages are forgotten, not compressed. |
| `SUMMARY_TRIGGER_TOKENS` | 4000 | Unsummarized tokens before summarizing runs. |
| `SUMMARY_KEEP_RECENT_TOKENS` | 1500 | Newest tokens always kept verbatim. |
| `SUMMARY_MAX_TOKENS` | 512 | Length limit for the summary. |

`config.py` refuses to start the app if these do not add up, because every one of
these mistakes is **silent** at runtime — you get a model that forgets things or
ignores instructions, not an error:

1. `AGENT_HISTORY_MAX_TOKENS + AGENT_MAX_OUTPUT_TOKENS` must fit `OLLAMA_NUM_CTX`.
   Otherwise Ollama trims the front of the prompt without telling you.
2. A maximum-length message must fit `AGENT_HISTORY_MAX_TOKENS` on its own, or
   long messages could never be answered.
3. `SUMMARY_TRIGGER_TOKENS` must be below
   `AGENT_HISTORY_MAX_TOKENS - SUMMARY_MAX_TOKENS`. Summarizing only preserves
   messages while they still fit the prompt; trigger too late and they are
   dropped for space first, and nothing can recover them.
4. `SUMMARY_KEEP_RECENT_TOKENS` must be below `SUMMARY_TRIGGER_TOKENS`, or
   nothing is ever old enough to summarize.

---

## What to watch in the logs

| Line | Meaning |
| --- | --- |
| `Summary updated: ...` | Normal. Shows tokens replaced. |
| `Summarizer returned nothing` | The model gave nothing usable. Harmless; retried next turn. |
| `Dropped N unsummarized message(s) for space` | **Real problem.** History is being forgotten. Lower the trigger or raise the budget. |
| `Could not update summary` | Summarizing failed. The answer still went out. |

---

## Things left simple on purpose

These are choices, not oversights.

**Tool calls are not stored.** The model does not see what a tool returned in an
earlier turn. Tools work normally inside a single turn.

**Summarizing runs inline.** On the turns where it fires, the caller waits for a
second model call. Moving it to a background task is the natural next step.

**`next_seq()` reads `MAX(seq) + 1`.** Two requests writing to one thread at the
exact same instant could pick the same number. The unique constraint on
`(thread_id, seq)` turns that into a clear error rather than jumbled messages.

**Token counts are estimates.** LangChain's `count_tokens_approximately`, not the
model's real tokenizer — Ollama does not expose one. Close enough because the
budgets leave slack.

**Summaries are overwritten, not versioned.** You cannot see what the summary
said three turns ago. A `thread_summaries` table keyed by `(thread_id, up_to_seq)`
would fix that if you ever need to audit or replay.

---

## Two non-obvious findings

Both were found by testing, and both look like mistakes in the code until you
know why.

**The summary is sent as a user/assistant pair, not a `SystemMessage`.** With
tools bound, the chat template fills the system slot with tool definitions and a
second system message is silently ignored — the model answers as though the
summary does not exist. Tested against the real agent:

| summary placement | result |
| --- | --- |
| `SystemMessage` | **failed** — "you haven't provided a revenue figure" |
| user + assistant pair | passed — "4.2 million" |
| folded into the question | passed — "4.2 million" |

**The summary model runs with `reasoning=False`.** Its `num_predict` is only
`SUMMARY_MAX_TOKENS`, and a reasoning model spends that entire budget thinking
and returns nothing at all. That showed up as `Summarizer returned nothing` on
every attempt until the flag was added.

---

## Where to start reading

1. `app/memory.py` — the whole idea, no I/O, about 130 lines.
2. `ChatService._build_prompt` — how memory is loaded.
3. `SummaryService.update_if_needed` — how compression decides.
4. `config.py`'s `token_budgets_must_add_up` — why the numbers matter.
