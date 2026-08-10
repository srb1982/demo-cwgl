class TestAuth:
    def test_login_wrong_password_400(self, client):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 400
        assert "错误" in r.json()["detail"]

    def test_login_unknown_user_400(self, client):
        r = client.post("/api/auth/login", json={"username": "no_such_user", "password": "x"})
        assert r.status_code == 400

    def test_login_missing_fields_422(self, client):
        assert client.post("/api/auth/login", json={"username": "admin"}).status_code == 422

    def test_admin_login_shape(self, client):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        body = r.json()
        assert "token" in body and "user" in body
        assert body["user"]["role"] == "admin"

    def test_me(self, client, admin_h):
        r = client.get("/api/auth/me", headers=admin_h)
        assert r.status_code == 200
        assert r.json()["username"] == "admin"

    def test_me_unauth_401(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_disabled_user_login_400(self, client, admin_h):
        client.post("/api/users", headers=admin_h, json={
            "username": "disabled1", "password": "123456", "real_name": "停用",
            "role": "viewer", "status": 0})
        r = client.post("/api/auth/login", json={"username": "disabled1", "password": "123456"})
        assert r.status_code == 400
        assert "禁用" in r.json()["detail"]

    def test_change_password_success(self, client, admin_h):
        client.post("/api/users", headers=admin_h, json={
            "username": "pwuser1", "password": "123456", "real_name": "改密", "role": "viewer"})
        assert client.post("/api/auth/login", json={"username": "pwuser1", "password": "123456"}).status_code == 200
        tok = client.post("/api/auth/login", json={"username": "pwuser1", "password": "123456"}).json()["token"]
        h = {"Authorization": f"Bearer {tok}"}
        r = client.post("/api/auth/change-password",
                        json={"old_password": "123456", "new_password": "newpass1"}, headers=h)
        assert r.status_code == 200
        assert client.post("/api/auth/login", json={"username": "pwuser1", "password": "123456"}).status_code == 400
        assert client.post("/api/auth/login", json={"username": "pwuser1", "password": "newpass1"}).status_code == 200

    def test_change_password_wrong_old_400(self, client, admin_h):
        r = client.post("/api/auth/change-password",
                        json={"old_password": "wrong", "new_password": "x"}, headers=admin_h)
        assert r.status_code == 400
        assert "原密码" in r.json()["detail"]

    def test_logout(self, client, admin_h):
        r = client.post("/api/auth/logout", headers=admin_h)
        assert r.status_code == 200
