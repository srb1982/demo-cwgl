import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth import get_current_user, require_roles, hash_password, get_client_ip
from ..config import ROLE_NAMES, ROLE_ADMIN
from ..database import query_all, query_one, execute
from ..services.audit import log_operation

router = APIRouter(prefix="/api/users", tags=["users"])


class UserBody(BaseModel):
    username: str = None
    real_name: str = ""
    role: str = "manager"
    phone: str = ""
    status: int = 1
    password: str = None


def _safe(rows):
    out = []
    for r in rows:
        out.append({
            "id": r["id"], "username": r["username"], "real_name": r["real_name"],
            "role": r["role"], "role_name": ROLE_NAMES.get(r["role"], r["role"]),
            "phone": r["phone"], "status": r["status"], "last_login": r["last_login"],
            "create_time": r["create_time"],
        })
    return out


@router.get("")
def list_users(user: dict = Depends(require_roles(ROLE_ADMIN))):
    rows = query_all("SELECT * FROM sys_user ORDER BY id")
    return _safe(rows)


@router.post("")
def create_user(body: UserBody, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="用户名和密码必填")
    if query_one("SELECT id FROM sys_user WHERE username=?", (body.username.strip(),)):
        raise HTTPException(status_code=400, detail="用户名已存在")
    if body.role not in ROLE_NAMES:
        raise HTTPException(status_code=400, detail="角色不合法")
    salt = os.urandom(8).hex()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute(
        "INSERT INTO sys_user(username,password_hash,salt,real_name,role,phone,status,create_time) VALUES(?,?,?,?,?,?,?,?)",
        (body.username.strip(), hash_password(body.password, salt), salt, body.real_name, body.role, body.phone, body.status, now),
    )
    log_operation(user, "新增用户", "用户管理", f"新增账号 {body.username}", get_client_ip(request))
    return {"message": "创建成功"}


@router.put("/{user_id}")
def update_user(user_id: int, body: UserBody, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    target = query_one("SELECT * FROM sys_user WHERE id=?", (user_id,))
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target["username"] == "admin" and body.status == 0:
        raise HTTPException(status_code=400, detail="不能禁用内置管理员")
    if body.role not in ROLE_NAMES:
        raise HTTPException(status_code=400, detail="角色不合法")
    execute("UPDATE sys_user SET real_name=?,role=?,phone=?,status=? WHERE id=?",
            (body.real_name, body.role, body.phone, body.status, user_id))
    log_operation(user, "修改用户", "用户管理", f"修改账号 {target['username']}", get_client_ip(request))
    return {"message": "修改成功"}


@router.put("/{user_id}/password")
def reset_password(user_id: int, body: UserBody, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    target = query_one("SELECT id FROM sys_user WHERE id=?", (user_id,))
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not body.password:
        raise HTTPException(status_code=400, detail="新密码必填")
    salt = os.urandom(8).hex()
    execute("UPDATE sys_user SET salt=?,password_hash=? WHERE id=?", (salt, hash_password(body.password, salt), user_id))
    log_operation(user, "重置密码", "用户管理", f"重置账号 {target['id']} 密码", get_client_ip(request))
    return {"message": "密码已重置"}


@router.delete("/{user_id}")
def delete_user(user_id: int, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    target = query_one("SELECT * FROM sys_user WHERE id=?", (user_id,))
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target["username"] == "admin":
        raise HTTPException(status_code=400, detail="不能删除内置管理员")
    if user["id"] == user_id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")
    execute("DELETE FROM sys_user WHERE id=?", (user_id,))
    log_operation(user, "删除用户", "用户管理", f"删除账号 {target['username']}", get_client_ip(request))
    return {"message": "删除成功"}
