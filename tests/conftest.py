import sys
import os
from sqlalchemy.engine import make_url
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from werkzeug.security import generate_password_hash
from app import create_app


@pytest.fixture
def app(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL")
    if url and not make_url(url).database.endswith("_test"):
        raise RuntimeError(
            "TEST_DATABASE_URL must point to a disposable database whose name ends in _test."
        )
    instance = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-key",
            "DATABASE_URL": url,
            "DATABASE_PATH": str(tmp_path / "test.sqlite3"),
            "ADMIN_PASSWORD_HASH": generate_password_hash("test-only-password"),
        }
    )
    yield instance
    if url:
        instance.extensions["database"].metadata.drop_all(
            instance.extensions["database"].engine
        )
    instance.extensions["database"].engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def headers(client):
    client.get("/")
    with client.session_transaction() as s:
        return {"X-CSRF-Token": s["csrf"]}
