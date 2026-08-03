import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import config
from .database import query_one
from .services import backup, warning_engine

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def _daily_warning_scan():
    try:
        result = warning_engine.scan_all()
        print(f"[预警扫描] 新增{result['added']} 自动办结{result['resolved']} 待办{result['pending']}")
    except Exception as e:
        print(f"[预警扫描] 异常: {e}")


def _daily_backup():
    try:
        info = backup.create_backup(manual=False)
        print(f"[自动备份] {info['name']} {info['size']} bytes")
    except Exception as e:
        print(f"[自动备份] 异常: {e}")


def _clean_old_backups():
    try:
        days = int(query_one("SELECT config_value FROM sys_config WHERE config_key='backup_days'")["config_value"] or 30)
        import time
        cutoff = time.time() - days * 86400
        if os.path.isdir(config.BACKUP_DIR):
            for fn in os.listdir(config.BACKUP_DIR):
                if fn.startswith("cw_backup_"):
                    fp = os.path.join(config.BACKUP_DIR, fn)
                    if os.path.getmtime(fp) < cutoff:
                        os.remove(fp)
    except Exception as e:
        print(f"[备份清理] 异常: {e}")


def init_scheduler():
    backup_time = "02:30"
    try:
        row = query_one("SELECT config_value FROM sys_config WHERE config_key='backup_time'")
        if row and row["config_value"]:
            backup_time = row["config_value"]
    except Exception:
        pass
    hh, mm = (backup_time.split(":") + ["0"])[:2]
    scheduler.add_job(_daily_warning_scan, CronTrigger(hour=6, minute=5), id="warning_scan", replace_existing=True)
    scheduler.add_job(_daily_backup, CronTrigger(hour=int(hh or 2), minute=int(mm or 30)), id="daily_backup", replace_existing=True)
    scheduler.add_job(_clean_old_backups, CronTrigger(hour=3, minute=0), id="clean_backups", replace_existing=True)
    if not scheduler.running:
        scheduler.start()
