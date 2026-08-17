from app.agents.graph import ChatAgent


class ChatService:

    def __init__(self, agent: ChatAgent):
        self.agent = agent

    async def chat(self, message: str) -> str:
        return await self.agent.run(message)