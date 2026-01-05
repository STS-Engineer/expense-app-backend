# app/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Expense API")
    ENV: str = os.getenv("ENV", "development")

    # DB
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: str = os.getenv("DB_PORT")
    DB_NAME: str = os.getenv("DB_NAME")
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_SSLMODE: str = os.getenv("DB_SSLMODE", "require")

    # FRONTEND
    FRONTEND_BASE_URL: str = os.getenv(
        "FRONTEND_BASE_URL",
        "http://localhost:5173"
    )

    # SMTP (OUTLOOK)
    SMTP_HOST: str = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "25"))
    SMTP_FROM: str = os.getenv("SMTP_FROM")
    SMTP_USER: str = os.getenv("SMTP_USER")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD")

settings = Settings()
