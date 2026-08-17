from contextlib import asynccontextmanager
from app.core.config import settings
from fastapi import FastAPI
from app.core.security import JWTService, PasswordService
from app.db.database import engine
from app.db.base import Base
from app.llm.ollama import OllamaLLM
from app.agents.graph import ChatAgent
from app.models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):

    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all
        )

    print("✅ Database initialized")

    # Security
    password_service = PasswordService()

    jwt_service = JWTService(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    app.state.password_service = password_service
    app.state.jwt_service = jwt_service

    # Application startup
    llm = OllamaLLM(
        model=settings.OLLAMA_AGENT_MODEL,
        streaming=False,
        temperature=0.7,
    )
    
    agent = ChatAgent(llm)

    app.state.llm = llm
    app.state.agent = agent
    
    print("LLM initialized")
    print("LangGraph agent initialized")

    yield

    # Shutdown
    print("🛑 Application shutting down")