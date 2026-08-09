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
