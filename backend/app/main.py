import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from socketio import ASGIApp

from . import config
from .seed import init_db
from .routers import (
    auth, users, menus, fields, ledger, archive, files, warning, fee, dashboard, system, launcher
)
from .services.sync import sio
from .scheduler import init_scheduler

init_db()

app = FastAPI(title="智慧乡村村务综合管理系统", docs_url="/api/docs", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(menus.router)
app.include_router(fields.router)
app.include_router(ledger.router)
app.include_router(archive.router)
app.include_router(files.router)
app.include_router(warning.router)
app.include_router(fee.router)
app.include_router(dashboard.router)
app.include_router(system.router)
app.include_router(launcher.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "name": "智慧乡村村务综合管理系统"}


# Socket.IO 实时同步挂载：前端连接 http://host:port/socket.io
app.mount("/socket.io", ASGIApp(sio, socketio_path=""))

# 生产模式：托管前端构建产物，实现单端口一体化部署（局域网 http://主机IP:8000）
STATIC_DIR = os.path.join(config.BASE_DIR, "static")
if os.path.isdir(STATIC_DIR):

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path:
            target = os.path.join(STATIC_DIR, full_path)
            if os.path.isfile(target) and not full_path.startswith("api/"):
                return FileResponse(target)
        index = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return {"detail": "前端尚未构建，请先执行前端构建并复制 dist 到 backend/static"}


@app.on_event("startup")
async def on_startup():
    init_scheduler()
