from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    LOG_LEVEL: str = "INFO"

    OLLAMA_AGENT_MODEL: str = "qwen3.5:2b-mlx"
    OLLAMA_EMBEDDING_MODEL: str = "qwen3-embedding:0.6b"
    OLLAMA_TEMPERATURE: float = 0.7

    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()