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

The agent is intentionally **stateless**: existing transcript messages are not sent back to the model, so a later request does not remember earlier turns. Threads currently group durable transcripts only. Conversation memory can be added later with a checkpointer or an explicit history-loading strategy.

The configured primary Ollama model must support native tool calling. Model execution is bounded by a shared concurrency limit, output-token cap, recursion limit, and total request timeout.

## Database migrations

Create and apply a migration after changing SQLAlchemy models:

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```
