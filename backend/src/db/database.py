import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./conciliaciones.db")

# SQLite needs check_same_thread=False; ignored for PostgreSQL
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from db.models import Conciliacion  # noqa: F401 — registers the model
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def _add_missing_columns():
    """Lightweight additive migration — no Alembic in this project. Only ever
    ADDs nullable columns that create_all() can't add to a pre-existing table."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "conciliaciones" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("conciliaciones")}
    if "estado_editable" not in existing:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE conciliaciones ADD COLUMN estado_editable JSON"))
