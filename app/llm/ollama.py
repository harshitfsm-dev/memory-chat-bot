from typing import Any

from langchain_ollama import ChatOllama


def create_ollama_model(
    model: str,
    *,
    timeout_seconds: float,
    **kwargs: Any,
) -> ChatOllama:
    return ChatOllama(
        model=model,
        async_client_kwargs={"timeout": timeout_seconds},
        **kwargs,
    )
