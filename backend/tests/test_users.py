import uuid


def _uniq(prefix):
    return f"{prefix}{uuid.uuid4().hex[:6]}"


def _login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def _create(client, admin_h, role="manager", password="pass1234"):
    username = _uniq("u")
    r = client.post("/api/users", headers=admin_h,
                    json={"username": username, "password": password, "real_name": "测试", "role": role})
    assert r.status_code == 200, r.text
    return username, password


class TestPermissions:
    def test_viewer_list_forbidden(self, client, viewer_h):
        assert client.get("/api/users", headers=viewer_h).status_code == 403

    def test_manager_list_forbidden(self, client, manager_h):
        assert client.get("/api/users", headers=manager_h).status_code == 403

    def test_viewer_create_forbidden(self, client, viewer_h):
        r = client.post("/api/users", headers=viewer_h, json={"username": _uniq("v"), "password": "x"})
        assert r.status_code == 403


class TestList:
    def test_list_shape_no_secrets(self, client, admin_h):
        r = client.get("/api/users", headers=admin_h)
        assert r.status_code == 200
        rows = r.json()
        assert any(u["username"] == "admin" for u in rows)
        assert all("password_hash" not in u and "salt" not in u for u in rows)
        assert all("role_name" in u for u in rows)


class TestCrud:
    def test_create_and_login(self, client, admin_h):
        username, password = _create(client, admin_h)
        r = _login(client, username, password)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "manager"

    def test_create_missing_fields_400(self, client, admin_h):
        assert client.post("/api/users", headers=admin_h, json={"username": _uniq("n")}).status_code == 400
        assert client.post("/api/users", headers=admin_h, json={"password": "x"}).status_code == 400

    def test_create_duplicate_username_400(self, client, admin_h):
        username, _ = _create(client, admin_h)
        r = client.post("/api/users", headers=admin_h, json={"username": username, "password": "y"})
        assert r.status_code == 400
        assert "已存在" in r.json()["detail"]

    def test_create_invalid_role_400(self, client, admin_h):
        r = client.post("/api/users", headers=admin_h, json={"username": _uniq("r"), "password": "x", "role": "boss"})
        assert r.status_code == 400

    def test_update_user(self, client, admin_h):
        username, _ = _create(client, admin_h)
        uid = _uid(client, admin_h, username)
        r = client.put(f"/api/users/{uid}", headers=admin_h, json={"real_name": "改名", "role": "viewer", "phone": "138", "status": 1})
        assert r.status_code == 200
        row = next(u for u in client.get("/api/users", headers=admin_h).json() if u["username"] == username)
        assert row["role"] == "viewer" and row["real_name"] == "改名" and row["phone"] == "138"

    def test_update_missing_404(self, client, admin_h):
        r = client.put("/api/users/999999", headers=admin_h, json={"real_name": "x", "role": "manager", "phone": "", "status": 1})
        assert r.status_code == 404

    def test_cannot_disable_admin(self, client, admin_h):
        r = client.put("/api/users/1", headers=admin_h, json={"real_name": "管理员", "role": "admin", "phone": "", "status": 0})
        assert r.status_code == 400
        assert "内置管理员" in r.json()["detail"]

    def test_update_invalid_role_400(self, client, admin_h):
        username, _ = _create(client, admin_h)
        uid = _uid(client, admin_h, username)
        r = client.put(f"/api/users/{uid}", headers=admin_h,
                       json={"real_name": "x", "role": "hacker", "phone": "", "status": 1})
        assert r.status_code == 400
        assert "角色" in r.json()["detail"]


class TestPassword:
    def test_reset_password(self, client, admin_h):
        username, password = _create(client, admin_h)
        uid = _uid(client, admin_h, username)
        r = client.put(f"/api/users/{uid}/password", headers=admin_h, json={"password": "newpass"})
        assert r.status_code == 200
        assert _login(client, username, password).status_code == 400
        assert _login(client, username, "newpass").status_code == 200

    def test_reset_missing_404(self, client, admin_h):
        r = client.put("/api/users/999999/password", headers=admin_h, json={"password": "x"})
        assert r.status_code == 404

    def test_reset_empty_400(self, client, admin_h):
        r = client.put("/api/users/2/password", headers=admin_h, json={"password": ""})
        assert r.status_code == 400


class TestDelete:
    def test_delete_user(self, client, admin_h):
        username, password = _create(client, admin_h)
        uid = _uid(client, admin_h, username)
        assert client.delete(f"/api/users/{uid}", headers=admin_h).status_code == 200
        assert _login(client, username, password).status_code == 400

    def test_cannot_delete_admin(self, client, admin_h):
        r = client.delete("/api/users/1", headers=admin_h)
        assert r.status_code == 400
        assert "内置管理员" in r.json()["detail"]

    def test_cannot_delete_self(self, client, admin_h):
        r = client.delete("/api/users/1", headers=admin_h)
        assert r.status_code == 400

    def test_delete_missing_404(self, client, admin_h):
        r = client.delete("/api/users/999999", headers=admin_h)
        assert r.status_code == 404


def _uid(client, admin_h, username):
    rows = client.get("/api/users", headers=admin_h).json()
    return next(u["id"] for u in rows if u["username"] == username)
