from fastapi import FastAPI

from app.core.lifespan import lifespan
from app.routers.chat_router import router as chat_router
from app.routers.user_router import router as user_router
from app.routers.auth_router import router as auth_router


app = FastAPI(
    title="Agent API",
    description=(
        "Ollama-powered agent responses."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


app.include_router(user_router)
app.include_router(auth_router)
app.include_router(chat_router)