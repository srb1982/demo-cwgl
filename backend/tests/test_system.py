class TestPermissions:
    def test_viewer_backup_forbidden(self, client, viewer_h):
        assert client.post("/api/system/backup", headers=viewer_h).status_code == 403

    def test_manager_logs_forbidden(self, client, manager_h):
        assert client.get("/api/system/logs", headers=manager_h).status_code == 403

    def test_viewer_config_forbidden(self, client, viewer_h):
        assert client.get("/api/system/config", headers=viewer_h).status_code == 403

    def test_viewer_screen_put_forbidden(self, client, viewer_h):
        r = client.put("/api/system/screen-config", headers=viewer_h, json={"config": {"a": 1}})
        assert r.status_code == 403


class TestBackup:
    def test_backup_create_and_list(self, client, admin_h):
        r = client.post("/api/system/backup", headers=admin_h)
        assert r.status_code == 200
        name = r.json()["name"]
        assert name.startswith("cw_backup_")
        backups = client.get("/api/system/backups", headers=admin_h).json()
        assert any(b["name"] == name for b in backups)

    def test_restore_missing_404(self, client, admin_h):
        r = client.post("/api/system/restore", headers=admin_h, json={"name": "no_such.zip"})
        assert r.status_code == 404


class TestConfig:
    def test_get_config_shape(self, client, admin_h):
        r = client.get("/api/system/config", headers=admin_h)
        assert r.status_code == 200
        body = r.json()
        assert "config" in body and "list" in body
        assert "village_name" in body["config"]

    def test_set_and_get(self, client, admin_h):
        r = client.put("/api/system/config", headers=admin_h, json={"key": "village_name", "value": "测试村"})
        assert r.status_code == 200
        body = client.get("/api/system/config", headers=admin_h).json()
        assert body["config"]["village_name"] == "测试村"

    def test_set_missing_key_404(self, client, admin_h):
        r = client.put("/api/system/config", headers=admin_h, json={"key": "no_such_key", "value": "x"})
        assert r.status_code == 404


class TestLogs:
    def test_logs_structure(self, client, admin_h):
        r = client.get("/api/system/logs", headers=admin_h)
        assert r.status_code == 200
        body = r.json()
        assert "total" in body and "list" in body
        assert body["total"] >= 0
        assert len(body["list"]) <= 15

    def test_logs_keyword(self, client, admin_h):
        r = client.get("/api/system/logs?keyword=登录", headers=admin_h)
        assert r.status_code == 200
        assert r.json()["total"] >= 0


class TestScreen:
    def test_screen_config_roundtrip(self, client, admin_h):
        cfg = {"layout": "top", "cards": ["population", "fee"]}
        r = client.put("/api/system/screen-config", headers=admin_h, json={"config": cfg})
        assert r.status_code == 200
        got = client.get("/api/system/screen-config", headers=admin_h)
        assert got.status_code == 200
        assert got.json() == cfg

    def test_screen_viewer_readable(self, client, viewer_h):
        assert client.get("/api/system/screen-config", headers=viewer_h).status_code == 200
