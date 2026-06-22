import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get absolute path to the backend directory to locate .env file correctly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE_PATH = os.path.join(BASE_DIR, ".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    WHATSAPP_VERIFY_TOKEN: str = "whatsapp_verify_token_5678"
    WHATSAPP_APP_SECRET: str = "863cab60cfa33cb49a675563ef1c0c78"
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    
    # AI Integration
    GEMINI_API_KEY: str = ""
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    REDIS_URL: str = "redis://localhost:6379"
    JWT_SECRET: str = "your-super-secret-jwt-key"

settings = Settings()
