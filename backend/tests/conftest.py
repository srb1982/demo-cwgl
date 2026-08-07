import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp(prefix="cw_test_")
import app.config as config

config.DATA_DIR = _tmp
config.DB_PATH = os.path.join(_tmp, "test.db")
config.UPLOAD_DIR = os.path.join(_tmp, "uploads")
config.BACKUP_DIR = os.path.join(_tmp, "backups")
os.makedirs(config.UPLOAD_DIR, exist_ok=True)
os.makedirs(config.BACKUP_DIR, exist_ok=True)

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def login(client):
    def _login(username, password):
        r = client.post("/api/auth/login", json={"username": username, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['token']}"}
    return _login


@pytest.fixture(scope="session")
def admin_h(login):
    return login("admin", "admin123")


@pytest.fixture(scope="session")
def manager_h(login):
    return login("mgr1", "123456")


@pytest.fixture(scope="session")
def viewer_h(login):
    return login("reader1", "123456")
