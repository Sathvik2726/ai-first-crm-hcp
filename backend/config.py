import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-First CRM HCP Module"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./hcp_crm.db")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    MOCK_AI_MODE: bool = os.getenv("MOCK_AI_MODE", "True").lower() in ("true", "1", "yes")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
