import hashlib
import secrets
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from . import config
from .database import query_one

bearer = HTTPBearer(auto_error=False)

SENSITIVE_FIELDS = {"id_card", "phone", "visa_no", "guardian_phone", "responsible_phone", "password"}


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()


def verify_password(password: str, salt: str, hashed: str) -> bool:
    return secrets.compare_digest(hash_password(password, salt), hashed)


def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=config.TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录或登录已失效")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except Exception:
        raise HTTPException(status_code=401, detail="无效的登录凭证")
    user = query_one("SELECT * FROM sys_user WHERE id=? AND status=1", (int(payload["sub"]),))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    return user


def require_roles(*roles):
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="当前账号无权限执行该操作")
        return user
    return _checker


def get_client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


def mask_value(field: str, value):
    if value is None:
        return value
    phone_fields = ("phone", "guardian_phone", "responsible_phone", "parent_phone", "emergency_phone", "helper_phone")
    if field not in ("id_card",) + phone_fields + ("visa_no",):
        return value
    s = str(value)
    if field == "id_card" and len(s) >= 15:
        return s[:4] + "*" * (len(s) - 8) + s[-4:]
    if field in phone_fields and len(s) == 11:
        return s[:3] + "****" + s[-4:]
    if field == "visa_no" and len(s) > 4:
        return s[:2] + "***" + s[-2:]
    return s


def apply_mask(rows, fields):
    result = []
    for r in rows:
        item = dict(r)
        for f in fields:
            if f in item:
                item[f] = mask_value(f, item[f])
        result.append(item)
    return result
