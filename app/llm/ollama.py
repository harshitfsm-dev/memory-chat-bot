from typing import Any

from langchain_ollama import ChatOllama, OllamaEmbeddings


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


def create_ollama_embeddings(
    model: str,
    *,
    dimensions: int,
    timeout_seconds: float,
) -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=model,
        dimensions=dimensions,
        async_client_kwargs={"timeout": timeout_seconds},
    )
