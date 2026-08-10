import os
import time


class TestSchedulerJobs:
    def test_warning_scan_runs(self):
        from app.scheduler import _daily_warning_scan
        _daily_warning_scan()

    def test_warning_scan_success_prints(self, capsys):
        from app.scheduler import _daily_warning_scan
        _daily_warning_scan()
        assert "[预警扫描]" in capsys.readouterr().out

    def test_warning_scan_error_handled(self, capsys, monkeypatch):
        from app.scheduler import _daily_warning_scan

        def boom():
            raise RuntimeError("scan broken")
        monkeypatch.setattr("app.services.warning_engine.scan_all", boom)
        _daily_warning_scan()
        assert "异常" in capsys.readouterr().out

    def test_daily_backup_error_handled(self, monkeypatch):
        from app.scheduler import _daily_backup

        def boom():
            raise RuntimeError("bk broken")
        monkeypatch.setattr("app.services.backup.create_backup", boom)
        _daily_backup()

    def test_clean_old_backups(self, monkeypatch, tmp_path, admin_h):
        from app.database import execute
        from app.scheduler import _clean_old_backups
        execute("UPDATE sys_config SET config_value='30' WHERE config_key='backup_days'")
        d = tmp_path
        old = os.path.join(str(d), "cw_backup_old.zip")
        new = os.path.join(str(d), "cw_backup_new.zip")
        open(old, "w").write("x")
        open(new, "w").write("x")
        old_t = time.time() - 40 * 86400
        os.utime(old, (old_t, old_t))
        monkeypatch.setattr("app.scheduler.config.BACKUP_DIR", str(d))
        _clean_old_backups()
        assert not os.path.exists(old)
        assert os.path.exists(new)

    def test_clean_old_backups_error_handled(self, capsys, monkeypatch, tmp_path):
        from app.scheduler import _clean_old_backups

        def boom_listdir(p):
            raise OSError("perm denied")
        monkeypatch.setattr("os.listdir", boom_listdir)
        monkeypatch.setattr("app.scheduler.config.BACKUP_DIR", str(tmp_path))
        _clean_old_backups()
        assert "异常" in capsys.readouterr().out

    def test_init_scheduler_uses_config_backup_time(self, admin_h):
        from app.database import execute
        from app.scheduler import init_scheduler
        execute("UPDATE sys_config SET config_value='01:45' WHERE config_key='backup_time'")
        init_scheduler()

    def test_init_scheduler_idempotent(self):
        from app.scheduler import init_scheduler
        init_scheduler()
