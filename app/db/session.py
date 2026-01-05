# app/db/session.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

from app.core.config import settings


# ✅ URL-encode password to handle special characters like @ $ !
encoded_password = quote_plus(settings.DB_PASSWORD)

DATABASE_URL = (
    f"postgresql+psycopg2://{settings.DB_USER}:"
    f"{encoded_password}@"
    f"{settings.DB_HOST}:"
    f"{settings.DB_PORT}/"
    f"{settings.DB_NAME}"
    f"?sslmode={settings.DB_SSLMODE}"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
