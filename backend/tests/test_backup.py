class TestBackupService:
    def test_auto_backup_filename(self):
        from app.services.backup import create_backup
        info = create_backup(manual=False)
        assert info["name"].endswith("_auto.zip")
        assert info["size"] > 0

    def test_restore_roundtrip(self, client, admin_h):
        from app.services.backup import create_backup
        client.post("/api/ledger/villager", headers=admin_h, json={"name": "还原甲", "gender": "男"})
        info = create_backup(manual=True)
        r = client.post("/api/system/restore", headers=admin_h, json={"name": info["name"]})
        assert r.status_code == 200
        assert client.get("/api/ledger/villager", headers=admin_h).status_code == 200

    def test_list_backups_empty_dir(self, monkeypatch):
        from app.services import backup
        monkeypatch.setattr(backup.config, "BACKUP_DIR", "/tmp/opencode/nonexist_bk_xxx")
        assert backup.list_backups() == []
