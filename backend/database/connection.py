import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# ------------------------------------------------------------
# Database configuration
# ------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "railway_block_planner")

    if not DB_PASSWORD:
        raise RuntimeError(
            "Database password is not configured. "
            "Set DB_PASSWORD or DATABASE_URL in .env."
        )

    DATABASE_URL = (
        f"postgresql://{quote_plus(DB_USER)}:"
        f"{quote_plus(DB_PASSWORD)}@"
        f"{DB_HOST}:{DB_PORT}/"
        f"{DB_NAME}"
    )

# ------------------------------------------------------------
# SQLAlchemy engine
# ------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# ------------------------------------------------------------
# Session
# ------------------------------------------------------------

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ------------------------------------------------------------
# Base model
# ------------------------------------------------------------

Base = declarative_base()


# ------------------------------------------------------------
# Database dependency
# ------------------------------------------------------------

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()