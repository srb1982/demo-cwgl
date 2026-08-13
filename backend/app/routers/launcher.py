from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import get_current_user, require_roles, get_client_ip
from ..config import ROLE_ADMIN
from ..database import query_one, execute, dumps
from ..services.audit import log_operation
from ..services import launcher

router = APIRouter(prefix="/api/system/launcher", tags=["launcher"])


class LauncherConfigBody(BaseModel):
    app_name: str = ""
    start_command: str = ""
    health_path: str = "/"
    start_port: int = 9000
    max_retries: int = 10
    pid_file: str = ""


def _save_config(cfg: dict):
    row = query_one("SELECT id FROM sys_config WHERE config_key='launcher_config'")
    value = dumps(cfg)
    if row:
        execute("UPDATE sys_config SET config_value=?, remark=? WHERE config_key='launcher_config'",
                (value, "通用局域网访问服务配置"))
    else:
        execute("INSERT INTO sys_config (config_key, config_value, remark) VALUES (?,?,?)",
                ("launcher_config", value, "通用局域网访问服务配置"))


@router.get("/status")
def status(user: dict = Depends(require_roles(ROLE_ADMIN))):
    snap = launcher.engine.snapshot()
    snap["config"] = launcher.load_config()
    return snap


@router.post("/start")
def start(user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    try:
        snap = launcher.engine.start()
    except launcher.LauncherError as e:
        raise HTTPException(status_code=400, detail=str(e))
    log_operation(user, "启动服务", "局域网访问", "通用服务启动", get_client_ip(request))
    return snap


@router.post("/enable-lan")
def enable_lan(user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    try:
        snap = launcher.engine.enable_lan()
    except launcher.LauncherError as e:
        raise HTTPException(status_code=400, detail=str(e))
    log_operation(user, "开启局域网", "局域网访问", "通用服务开放局域网访问", get_client_ip(request))
    return snap


@router.post("/stop")
def stop(user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    snap = launcher.engine.stop()
    log_operation(user, "停止服务", "局域网访问", "通用服务停止", get_client_ip(request))
    return snap


@router.get("/logs")
def logs(lines: int = 200, user: dict = Depends(require_roles(ROLE_ADMIN))):
    return {"logs": launcher.engine.log_lines(lines)}


@router.get("/config")
def get_config(user: dict = Depends(require_roles(ROLE_ADMIN))):
    return {"config": launcher.load_config()}


@router.put("/config")
def save_config(body: LauncherConfigBody, user: dict = Depends(require_roles(ROLE_ADMIN)),
                request: Request = None):
    if not body.start_command.strip():
        raise HTTPException(status_code=400, detail="启动命令不能为空")
    if not (0 < body.start_port < 65536):
        raise HTTPException(status_code=400, detail="起始端口需在 1-65535 之间")
    if body.max_retries < 1 or body.max_retries > 100:
        raise HTTPException(status_code=400, detail="最大尝试次数需在 1-100 之间")
    cfg = {
        "app_name": body.app_name.strip(),
        "start_command": body.start_command.strip(),
        "health_path": body.health_path.strip() or "/",
        "start_port": body.start_port,
        "max_retries": body.max_retries,
        "pid_file": body.pid_file.strip(),
    }
    _save_config(cfg)
    log_operation(user, "修改配置", "局域网访问", "修改通用服务启动配置", get_client_ip(request))
    return {"config": launcher.load_config()}


@router.get("/netcards")
def netcards(user: dict = Depends(require_roles(ROLE_ADMIN))):
    return {"netcards": launcher.get_netcards()}
