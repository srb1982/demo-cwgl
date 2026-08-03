import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..auth import get_current_user
from ..config import UPLOAD_DIR

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{path:path}")
def get_file(path: str, user: dict = Depends(get_current_user)):
    base = os.path.realpath(UPLOAD_DIR)
    target = os.path.realpath(os.path.join(UPLOAD_DIR, path))
    if not target.startswith(base + os.sep) and target != base:
        raise HTTPException(status_code=403, detail="非法文件路径")
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(target)
