# Chat Bot API

An authenticated FastAPI API that stores users in SQLite and generates chat responses with a local Ollama model.

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) with the configured chat model available locally

## Setup

```bash
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation.

If you already have the original prototype `chatbot.db`, its `users` table predates Alembic. Back it up, verify that it matches the initial migration, then run `uv run alembic stamp head` once instead of applying the initial migration.

## Configuration

| Variable | Required | Default |
| --- | --- | --- |
| `DATABASE_URL` | Yes | — |
| `JWT_SECRET_KEY` | Yes | — |
| `JWT_ALGORITHM` | No | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` |
| `OLLAMA_AGENT_MODEL` | No | `qwen3.5:2b-mlx` |
| `OLLAMA_TEMPERATURE` | No | `0.7` |
| `OLLAMA_TIMEOUT_SECONDS` | No | `30` |
| `LANGGRAPH_CHECKPOINT_PATH` | No | `langgraph_checkpoints.db` |
| `AGENT_TIMEOUT_SECONDS` | No | `90` |
| `AGENT_RECURSION_LIMIT` | No | `8` |
| `AGENT_HISTORY_MAX_TOKENS` | No | `4000` |
| `LOG_LEVEL` | No | `INFO` |
| `SQL_ECHO` | No | `false` |

Use a long, random JWT secret outside local development. Never commit `.env`.

## API flow

1. `POST /users/` creates an account.
2. `POST /auth/login` returns a bearer token.
3. `POST /chat/` accepts `{"message": "..."}` with that token.

The LangGraph workflow routes between the Ollama model and a safe UTC-time tool until it produces a final answer. Each authenticated user currently has one checkpointed conversation, so later requests automatically continue that user's existing chat without a client-managed session ID.

User identity is derived from the bearer token and scopes the internal checkpoint thread, preventing conversation history from leaking across accounts. The checkpoint database contains conversation content and should be protected and retained according to your application policy.

The configured Ollama model must support native tool calling. For multiple application workers, replace the SQLite checkpointer with a shared production checkpointer such as PostgreSQL.

## Database migrations

Create a migration after changing SQLAlchemy models:

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```
