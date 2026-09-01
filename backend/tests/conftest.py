import os
import sys
import tempfile
from pathlib import Path

# El DATABASE_URL se lee al importar db/database.py, así que hay que fijarlo
# ANTES de cualquier import del proyecto — corre en un sqlite temporal propio,
# nunca en conciliaciones.db (la base real de desarrollo del usuario).
_TEST_DB_DIR = tempfile.mkdtemp(prefix="conciliaciones_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_DIR}/test.db"

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    from db.database import init_db
    init_db()


@pytest.fixture()
def client():
    from main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_session():
    from db.database import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
