# backend/database.py
"""
Настройка подключения к базе данных PostgreSQL.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# URL базы данных
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://gpzu_user:gpzu_password@localhost:5432/gpzu_db"
)

# Создаем engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

# Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base для моделей
Base = declarative_base()


def get_db():
    """Dependency для FastAPI endpoints"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Создает все таблицы"""
    from models.application import Application
    from models.gp import GP
    from models.refusal import Refusal
    from models.tu_request import TuRequest
    
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы созданы")
