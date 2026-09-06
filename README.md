# Chat Bot API

An authenticated FastAPI API that stores users and chat transcripts in PostgreSQL and generates responses with local Ollama models.

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- [Docker](https://www.docker.com/) for PostgreSQL
- [Ollama](https://ollama.com/) with the configured models available locally

## Setup

```bash
uv sync
cp .env.example .env
docker-compose up -d
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation.

## Configuration

| Variable                          | Required | Default                   |
| --------------------------------- | -------- | ------------------------- |
| `DATABASE_URL`                    | Yes      | —                         |
| `JWT_SECRET_KEY`                  | Yes      | — (minimum 32 characters) |
| `JWT_ALGORITHM`                   | No       | `HS256`                   |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No       | `30`                      |
| `OLLAMA_AGENT_MODEL`              | No       | `deepseek-r1:14b`         |
| `OLLAMA_SMALL_AGENT_MODEL`        | No       | `llama3.2:3b`             |
| `OLLAMA_TEMPERATURE`              | No       | `0.7`                     |
| `OLLAMA_TIMEOUT_SECONDS`          | No       | `30`                      |
| `AGENT_TIMEOUT_SECONDS`           | No       | `90`                      |
| `AGENT_MAX_CONCURRENCY`           | No       | `2`                       |
| `AGENT_MAX_OUTPUT_TOKENS`         | No       | `1024`                    |
| `AGENT_TITLE_TIMEOUT_SECONDS`     | No       | `15`                      |
| `AGENT_TITLE_MAX_TOKENS`          | No       | `24`                      |
| `AGENT_RECURSION_LIMIT`           | No       | `8`                       |
| `AGENT_HISTORY_MAX_TOKENS`        | No       | `4000`                    |
| `LOG_LEVEL`                       | No       | `INFO`                    |
| `SQL_ECHO`                        | No       | `false`                   |

Use a long, random JWT secret outside local development. Never commit `.env`.
Production deployments should install the exact locked dependencies with `uv sync --frozen`.

## API flow

1. `POST /users/` creates an account.
2. `POST /auth/login` returns a bearer token.
3. `POST /chat/` accepts `{"message": "..."}` with that token.
4. Omit `thread_id` to create a thread, or pass an owned thread UUID to append to its transcript.

Thread ownership is checked on every request. A missing or unowned thread returns `404` without revealing whether another user owns it. User and assistant messages are persisted in `chat_messages`.

A write that the database rejects returns `503` and is safe to retry.

## Transactions

Repositories stage work on the request-scoped session; services decide when it
becomes durable through `UnitOfWork`. A chat request therefore uses two
transactions rather than one:

1. The thread (when new) and the user's message commit together, so a failed
   insert cannot leave an empty thread behind.
2. The assistant's message commits after generation.

The split is deliberate. Committing releases the pooled database connection, so
no connection stays checked out during model inference or while queueing for an
execution slot. A single request-wide transaction would pin one for the full
`AGENT_TIMEOUT_SECONDS` budget and exhaust the pool under load.

Committing before generation also means a user's turn survives a failed or
timed-out response, so the transcript reflects what they actually submitted.

The configured primary Ollama model must support native tool calling. Model execution is bounded by a shared concurrency limit, output-token cap, recursion limit, and total request timeout.

## Short-term memory

The agent stores nothing between requests. Memory is rebuilt on every turn from
what is in the database, which means the prompt is always something you can go
look at in SQL.

Each turn sends the model three things, in this order:

1. A summary of the older messages, if the thread has one.
2. The most recent `AGENT_HISTORY_MAX_MESSAGES` messages, word for word.
3. The new message.

Two columns make that possible. `chat_messages.seq` numbers messages within a
thread (1, 2, 3...), and `chat_threads.summary_up_to_seq` records how far the
summary already reaches. The replay window only loads messages with a higher
`seq`, so nothing is described twice — once in the summary and once verbatim.

`seq` exists instead of ordering by `created_at` because messages saved in the
same transaction share a timestamp, which leaves their order undefined.

Three files hold it all:

| File | What it does |
| --- | --- |
| `app/memory.py` | Plain functions: database rows in, LangChain messages out. No I/O, easy to read. |
| `app/services/summary_service.py` | Decides when to summarize and writes the summary. |
| `app/services/chat_service.py` | `_build_prompt`, `_save_message`, `_update_summary`. |

### Summarizing older messages

Once a thread has `SUMMARY_TRIGGER_MESSAGES` messages the summary does not cover,
everything except the newest `SUMMARY_KEEP_RECENT_MESSAGES` is folded into it. The
recent ones stay word for word because follow-up questions point at them
("that one", "make it 5"), and rewording breaks those references.

Summarizing is incremental: the model sees the previous summary plus only the new
messages, never the whole thread, so the prompt stays small however long the
conversation runs.

It runs after the turn is already saved and its errors are caught and logged, so
a failed summary never breaks a chat — the same messages are simply tried again
after the next turn. It does mean the caller waits for a second model call on the
turns where it fires. Moving it to a background task is the natural next step.

Startup refuses to boot if `SUMMARY_TRIGGER_MESSAGES` is above
`AGENT_HISTORY_MAX_MESSAGES`. Summarizing only preserves messages while they are
still being replayed; if the trigger were higher, messages would fall out of the
window before anything summarized them and would be lost.

### Things left simple on purpose

- Tool calls are not stored, so the model does not see what a tool returned in an
  earlier turn. Tools still work normally within a single turn.
- `next_seq()` reads `MAX(seq) + 1`. Two requests writing to one thread at the
  exact same moment could pick the same number; the unique constraint on
  `(thread_id, seq)` turns that into a clear error rather than jumbled messages.
- Prompt size is capped by `TrimHistoryMiddleware` using LangChain's approximate
  token counting, not a real tokenizer.
- `OLLAMA_NUM_CTX` is set explicitly. Ollama's default is 4096 whatever the model
  supports, and a longer prompt gets its beginning cut off silently, system
  prompt first — which looks like a model ignoring its instructions.

## Database migrations

Create and apply a migration after changing SQLAlchemy models:

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```
