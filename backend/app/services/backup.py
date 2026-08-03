import io
import os
import shutil
import zipfile
from datetime import datetime

from .. import config

BACKUP_PASSWORD = "CW2026"

def _stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_backup(manual=False) -> dict:
    stamp = _stamp()
    name = f"cw_backup_{stamp}{'_manual' if manual else '_auto'}.zip"
    path = os.path.join(config.BACKUP_DIR, name)
    _write_zip(path)
    return {"name": name, "path": path, "size": os.path.getsize(path), "time": stamp}


def _write_zip(path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(config.DB_PATH):
            zf.write(config.DB_PATH, "village.db")
        if os.path.isdir(config.UPLOAD_DIR):
            for root, _dirs, files in os.walk(config.UPLOAD_DIR):
                for fn in files:
                    fp = os.path.join(root, fn)
                    zf.write(fp, os.path.join("uploads", os.path.relpath(fp, config.UPLOAD_DIR)))


def restore_backup(name: str) -> bool:
    path = os.path.join(config.BACKUP_DIR, os.path.basename(name))
    if not os.path.exists(path):
        raise FileNotFoundError("备份文件不存在")
    # 备份现有数据
    keep = os.path.join(config.BACKUP_DIR, f"pre_restore_{_stamp()}.zip")
    _write_zip(keep)
    # 恢复
    tmp_dir = os.path.join(config.DATA_DIR, "_restore_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(path, "r") as zf:
            for m in zf.namelist():
                zf.extract(m, tmp_dir)
        db_src = os.path.join(tmp_dir, "village.db")
        if os.path.exists(db_src):
            shutil.copy(db_src, config.DB_PATH)
        up_src = os.path.join(tmp_dir, "uploads")
        if os.path.isdir(up_src):
            shutil.rmtree(config.UPLOAD_DIR, ignore_errors=True)
            shutil.copytree(up_src, config.UPLOAD_DIR)
        return True
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def list_backups() -> list:
    items = []
    if not os.path.isdir(config.BACKUP_DIR):
        return items
    for fn in sorted(os.listdir(config.BACKUP_DIR), reverse=True):
        if fn.startswith("cw_backup_"):
            fp = os.path.join(config.BACKUP_DIR, fn)
            items.append({"name": fn, "size": os.path.getsize(fp), "time": datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")})
    return items
