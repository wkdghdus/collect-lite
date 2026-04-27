import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.workers import jobs as jobs_module


# Teach SQLite how to handle PostgreSQL-specific types
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Background-task workers open their own session via app.db.SessionLocal, which
# bypasses the dependency_overrides path used for request handlers. Repoint the
# worker module to the test engine so BackgroundTasks write to the same DB the
# test session reads from.
jobs_module.SessionLocal = TestingSessionLocal


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
