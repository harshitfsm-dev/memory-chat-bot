# llm/ollama.py

from typing import Any

from langchain_ollama import ChatOllama

from app.llm.base import BaseLLM


class OllamaLLM(BaseLLM):

    def __init__(
        self,
        model: str,
        streaming: bool = False,
        **kwargs: Any,
    ):
        self.model = model
        self.streaming = streaming

        self.client = ChatOllama(
            model=model,
            **kwargs,
        )

    async def generate(self, prompt: str) -> str:
        response = await self.client.ainvoke(prompt)
        return response.content