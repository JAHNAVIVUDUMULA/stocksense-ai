import os
from pathlib import Path
from dotenv import load_dotenv

# Locate .env file relative to this file
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "StockSense AI")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./stocksense.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "stocksense_ai_dev_secret_key_super_secure_2026_aiml")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

settings = Settings()
