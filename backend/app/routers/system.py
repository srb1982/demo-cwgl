from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth import get_current_user, require_roles, get_client_ip
from ..config import ROLE_ADMIN
from ..database import query_all, query_one, execute, dumps, loads, get_db
from ..seed import LEDGERS
from ..services.audit import log_operation
from ..services.backup import create_backup, list_backups, restore_backup
from ..services.sync import notify_data_changed

router = APIRouter(prefix="/api/system", tags=["system"])


# ---------------- 备份恢复 ----------------
@router.post("/backup")
async def manual_backup(user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    info = create_backup(manual=True)
    log_operation(user, "手动备份", "系统运维", f"创建备份 {info['name']}", get_client_ip(request))
    return {"message": "备份创建成功", "name": info["name"]}


@router.get("/backups")
def backups(user: dict = Depends(require_roles(ROLE_ADMIN))):
    return list_backups()


class RestoreBody(BaseModel):
    name: str


@router.post("/restore")
async def restore(body: RestoreBody, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    try:
        restore_backup(body.name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复失败：{e}")
    log_operation(user, "数据恢复", "系统运维", f"从备份 {body.name} 恢复数据", get_client_ip(request))
    await notify_data_changed(module="system")
    return {"message": "恢复成功，系统数据已还原为备份状态"}


# ---------------- 操作日志 ----------------
@router.get("/logs")
def oper_logs(page: int = 1, size: int = 15, module: str = "", keyword: str = "",
              user: dict = Depends(require_roles(ROLE_ADMIN))):
    where, params = ["1=1"], []
    if module:
        where.append("module LIKE ?")
        params.append(f"%{module}%")
    if keyword:
        where.append("(username LIKE ? OR detail LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql = " WHERE " + " AND ".join(where)
    total = query_one(f"SELECT COUNT(*) c FROM sys_oper_log{sql}", params)["c"]
    rows = query_all(f"SELECT * FROM sys_oper_log{sql} ORDER BY id DESC LIMIT ? OFFSET ?", params + [size, (page - 1) * size])
    return {"total": total, "page": page, "size": size, "list": rows}


# ---------------- 系统参数 ----------------
@router.get("/config")
def get_config(user: dict = Depends(require_roles(ROLE_ADMIN))):
    rows = query_all("SELECT config_key,config_value,remark FROM sys_config")
    data = {}
    for r in rows:
        data[r["config_key"]] = r["config_value"]
    return {"config": data, "list": rows}


class ConfigBody(BaseModel):
    key: str
    value: str


@router.put("/config")
async def set_config(body: ConfigBody, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    row = query_one("SELECT id FROM sys_config WHERE config_key=?", (body.key,))
    if not row:
        raise HTTPException(status_code=404, detail="参数不存在")
    execute("UPDATE sys_config SET config_value=? WHERE config_key=?", (body.value, body.key))
    log_operation(user, "系统配置", "系统运维", f"修改参数 {body.key} = {body.value}", get_client_ip(request))
    await notify_data_changed(module="config")
    return {"message": "配置已保存"}


# ---------------- 年度数据封存 ----------------
class ArchiveYearBody(BaseModel):
    year: str


@router.post("/archive-year")
async def archive_year(body: ArchiveYearBody, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    if not body.year or not body.year.isdigit():
        raise HTTPException(status_code=400, detail="年度格式不正确")
    year = body.year
    # 封存前先自动备份，确保可回退
    create_backup(manual=True)
    tables = [lg["table"] for lg in LEDGERS]
    archived = []
    with get_db() as db:
        for t in tables:
            archive_tbl = f"{t}_{year}"
            cur = db.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (archive_tbl,))
            if not cur.fetchone():
                db.execute(f"CREATE TABLE {archive_tbl} AS SELECT * FROM {t} WHERE 1=0")
            db.execute(f"INSERT INTO {archive_tbl} SELECT * FROM {t}")
            db.execute(f"DELETE FROM {t}")
            archived.append(archive_tbl)
    log_operation(user, "年度封存", "系统运维", f"封存 {year} 年度数据：{len(archived)} 张台账表已归档并清空", get_client_ip(request))
    await notify_data_changed(module="system")
    return {"message": f"{year} 年度数据已封存（{len(archived)} 张台账表），原表已清空，封存前已自动备份"}


# ---------------- 大屏布局配置 ----------------
@router.get("/screen-config")
def screen_config(user: dict = Depends(get_current_user)):
    row = query_one("SELECT config_json FROM sys_screen_config WHERE screen_key='dashboard'")
    return loads(row["config_json"] if row else None, None) if row else None


class ScreenBody(BaseModel):
    config: dict


@router.put("/screen-config")
async def save_screen(body: ScreenBody, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    with get_db() as db:
        db.execute(
            "INSERT INTO sys_screen_config(screen_key,config_json,update_time) VALUES('dashboard',?,?) "
            "ON CONFLICT(screen_key) DO UPDATE SET config_json=?,update_time=?",
            (dumps(body.config), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             dumps(body.config), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
    log_operation(user, "保存大屏布局", "系统运维", "更新数据大屏布局", get_client_ip(request))
    await notify_data_changed(module="screen")
    return {"message": "大屏布局已保存"}
