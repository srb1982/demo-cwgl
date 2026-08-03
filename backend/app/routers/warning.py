import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..auth import get_current_user, require_roles, get_client_ip
from ..config import ROLE_ADMIN, ROLE_MANAGER
from ..database import query_all, query_one, execute
from ..services.audit import log_operation
from ..services.sync import notify_warning
from ..services.warning_engine import scan_all

router = APIRouter(prefix="/api/warnings", tags=["warnings"])

LEVEL_NAMES = {"green": "正常", "yellow": "预警", "red": "紧急"}
STATUS_NAMES = {"pending": "待办", "handled": "已办结", "resolved": "自动办结", "postponed": "已延期"}


def _fmt(r):
    return {
        "id": r["id"], "menu_code": r["menu_code"], "ledger_name": r["ledger_name"],
        "warning_type": r["warning_type"], "content": r["content"], "level": r["level"],
        "level_name": LEVEL_NAMES.get(r["level"], r["level"]), "status": r["status"],
        "status_name": STATUS_NAMES.get(r["status"], r["status"]), "due_date": r["due_date"],
        "create_time": r["create_time"], "handle_user": r["handle_user"], "handle_time": r["handle_time"],
        "remark": r["remark"],
    }


@router.get("")
def list_warnings(status: str = "", level: str = "", page: int = 1, size: int = 10, keyword: str = "",
                  user: dict = Depends(get_current_user)):
    where, params = ["1=1"], []
    if status:
        where.append("status=?")
        params.append(status)
    if level:
        where.append("level=?")
        params.append(level)
    if keyword:
        where.append("content LIKE ?")
        params.append(f"%{keyword}%")
    sql = " WHERE " + " AND ".join(where)
    total = query_one(f"SELECT COUNT(*) c FROM t_warning{sql}", params)["c"]
    rows = query_all(f"SELECT * FROM t_warning{sql} ORDER BY CASE level WHEN 'red' THEN 1 WHEN 'yellow' THEN 2 ELSE 3 END, id DESC LIMIT ? OFFSET ?",
                     params + [size, (page - 1) * size])
    return {"total": total, "page": page, "size": size, "list": [_fmt(r) for r in rows]}


@router.get("/summary")
def warning_summary(user: dict = Depends(get_current_user)):
    rows = query_all("SELECT level,status,COUNT(*) c FROM t_warning GROUP BY level,status")
    summary = {"green": 0, "yellow": 0, "red": 0, "pending": 0, "handled": 0, "total": 0}
    for r in rows:
        summary[r["level"]] = summary.get(r["level"], 0) + r["c"]
        if r["status"] == "pending":
            summary["pending"] += r["c"]
        if r["status"] == "handled":
            summary["handled"] += r["c"]
    summary["total"] = summary["red"] + summary["yellow"] + summary["green"]
    return summary


class HandleBody(BaseModel):
    remark: str = ""


@router.post("/{warn_id}/handle")
async def handle_warning(warn_id: int, body: HandleBody, user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)), request: Request = None):
    w = query_one("SELECT * FROM t_warning WHERE id=?", (warn_id,))
    if not w:
        raise HTTPException(status_code=404, detail="预警不存在")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute("UPDATE t_warning SET status='handled',handle_user=?,handle_time=?,remark=? WHERE id=?",
            (user["username"], now, body.remark, warn_id))
    log_operation(user, "办结预警", "预警中心", f"办结预警#{warn_id}", get_client_ip(request))
    await notify_warning()
    return {"message": "预警已办结"}


@router.post("/{warn_id}/postpone")
async def postpone_warning(warn_id: int, body: HandleBody, user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)), request: Request = None):
    w = query_one("SELECT * FROM t_warning WHERE id=?", (warn_id,))
    if not w:
        raise HTTPException(status_code=404, detail="预警不存在")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute("UPDATE t_warning SET status='postponed',handle_user=?,handle_time=?,remark=? WHERE id=?",
            (user["username"], now, body.remark, warn_id))
    log_operation(user, "延期预警", "预警中心", f"延期预警#{warn_id}", get_client_ip(request))
    await notify_warning()
    return {"message": "预警已延期处理"}


@router.post("/scan")
async def manual_scan(user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)), request: Request = None):
    result = scan_all()
    log_operation(user, "手动扫描", "预警中心", f"触发扫描：新增{result['added']} 自动办结{result['resolved']}", get_client_ip(request))
    await notify_warning()
    return {"message": f"扫描完成：新增预警 {result['added']} 条，自动办结 {result['resolved']} 条"}


@router.get("/export")
def export_warnings(user: dict = Depends(get_current_user)):
    from openpyxl import Workbook
    rows = query_all("SELECT * FROM t_warning ORDER BY id DESC")
    wb = Workbook()
    ws = wb.active
    ws.title = "预警清单"
    ws.append(["ID", "台账", "类型", "内容", "等级", "状态", "截止日期", "生成时间", "处理人", "处理时间", "备注"])
    for r in rows:
        ws.append([r["id"], r["ledger_name"], r["warning_type"], r["content"],
                   LEVEL_NAMES.get(r["level"]), STATUS_NAMES.get(r["status"]), r["due_date"],
                   r["create_time"], r["handle_user"], r["handle_time"], r["remark"]])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=warnings.xlsx"})
