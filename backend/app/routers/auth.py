from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth import create_token, get_current_user, hash_password, verify_password, get_client_ip
from ..database import query_one, execute
from ..services.audit import log_operation

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


class ChangePwdBody(BaseModel):
    old_password: str
    new_password: str


def safe_user(u: dict) -> dict:
    return {
        "id": u["id"],
        "username": u["username"],
        "real_name": u["real_name"],
        "role": u["role"],
        "phone": u["phone"],
        "status": u["status"],
    }


@router.post("/login")
async def login(body: LoginBody, request: Request):
    user = query_one("SELECT * FROM sys_user WHERE username=?", (body.username.strip(),))
    if not user:
        log_operation(None, "登录", "认证", f"用户 {body.username} 登录失败：账号不存在", get_client_ip(request))
        raise HTTPException(status_code=400, detail="账号或密码错误")
    if user["status"] != 1:
        raise HTTPException(status_code=400, detail="账号已被禁用，请联系管理员")
    if not verify_password(body.password, user["salt"], user["password_hash"]):
        log_operation(user, "登录", "认证", "登录失败：密码错误", get_client_ip(request))
        raise HTTPException(status_code=400, detail="账号或密码错误")
    token = create_token(user["id"], user["username"], user["role"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute("UPDATE sys_user SET last_login=? WHERE id=?", (now, user["id"]))
    log_operation(user, "登录", "认证", "登录成功", get_client_ip(request))
    return {"token": token, "user": {**safe_user(user), "last_login": now}}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return safe_user(user)


@router.post("/change-password")
async def change_password(body: ChangePwdBody, user: dict = Depends(get_current_user), request: Request = None):
    if not verify_password(body.old_password, user["salt"], user["password_hash"]):
        raise HTTPException(status_code=400, detail="原密码错误")
    salt = hash_password(body.new_password, user["salt"])
    execute("UPDATE sys_user SET password_hash=? WHERE id=?", (hash_password(body.new_password, user["salt"]), user["id"]))
    log_operation(user, "修改密码", "认证", "修改登录密码", get_client_ip(request))
    return {"message": "密码修改成功"}


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user), request: Request = None):
    log_operation(user, "退出登录", "认证", "退出系统", get_client_ip(request))
    return {"message": "已退出"}
