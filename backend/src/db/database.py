import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./conciliaciones.db")

POSTGRES_CONNECT_TIMEOUT_SECONDS = 10

# SQLite needs check_same_thread=False; PostgreSQL gets a timeout so an
# unreachable DB fails startup fast instead of hanging the server.
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {"connect_timeout": POSTGRES_CONNECT_TIMEOUT_SECONDS}

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


_COLUMNAS_AGREGADAS = {
    "conciliaciones": {"estado_editable": "JSON"},
    "bancos":         {"formato_mayor": "JSON", "formato_extracto": "JSON"},
}


def _add_missing_columns():
    """Lightweight additive migration — no Alembic in this project. Only ever
    ADDs nullable columns that create_all() can't add to a pre-existing table."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    for tabla, columnas in _COLUMNAS_AGREGADAS.items():
        if tabla not in tablas:
            continue
        existentes = {c["name"] for c in inspector.get_columns(tabla)}
        for columna, tipo in columnas.items():
            if columna in existentes:
                continue
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}"))
