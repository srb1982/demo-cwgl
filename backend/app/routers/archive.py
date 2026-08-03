import os
import re
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..auth import get_current_user, require_roles, get_client_ip
from ..config import UPLOAD_DIR, ROLE_ADMIN, ROLE_MANAGER
from ..database import query_all, query_one, execute, get_db
from ..services.audit import log_operation
from ..services.sync import notify_data_changed

router = APIRouter(prefix="/api/archive", tags=["archive"])

WRITABLE = [ROLE_ADMIN, ROLE_MANAGER]
ALLOW_EXT = {".doc", ".docx", ".xls", ".xlsx", ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip", ".txt"}

CATEGORY_KEYWORDS = {
    "villager": ["村民", "人口", "户口", "居民", "花名册"],
    "party_member": ["党员", "入党", "党费", "支部", "积极分子"],
    "disabled": ["残疾", "残疾人证", "残疾证"],
    "low_income": ["低保", "最低生活保障"],
    "fee_collect": ["三费", "医保", "养老保险", "大病补充", "缴费"],
    "reservoir_migrant": ["水库移民", "移民"],
    "village_move": ["搬迁", "安置"],
    "rescue": ["救助", "临时救助", "医疗救助"],
    "left_child": ["留守", "儿童"],
    "elderly": ["老年", "高龄", "补贴"],
    "veteran": ["退伍", "退役军人", "军人", "优抚"],
    "oversea": ["出境", "境外", "签证"],
    "three_capital": ["三资", "集体资产", "集体经济"],
    "homestead": ["宅基地", "建房", "房屋"],
    "drowning_prevent": ["防溺水", "溺水", "水域"],
    "petition": ["信访", "矛盾", "纠纷"],
    "village_public": ["公示", "公开", "公告"],
    "public_job": ["公益岗位", "公益岗"],
    "custom_rural": ["红白事", "移风易俗", "简办"],
    "rural_industry": ["产业", "合作社", "集体经济项目"],
    "project": ["工程", "项目", "施工", "标段"],
    "visit_record": ["走访", "帮扶", "慰问"],
}

CATEGORY_NAMES = {
    "villager": "村民信息", "party_member": "党员信息", "disabled": "残疾人", "low_income": "低保",
    "fee_collect": "三费收缴", "reservoir_migrant": "水库移民", "village_move": "搬迁",
    "rescue": "困难救助", "left_child": "留守儿童", "elderly": "老年人", "veteran": "退役军人",
    "oversea": "境外人员", "three_capital": "三资管理", "homestead": "宅基地建房",
    "drowning_prevent": "防溺水", "petition": "信访矛盾", "village_public": "村务公开",
    "public_job": "公益岗位", "custom_rural": "移风易俗", "rural_industry": "乡村产业",
    "project": "工程项目", "visit_record": "走访帮扶",
}


def auto_classify(filename: str) -> str:
    base = os.path.splitext(filename)[0]
    for code, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in base:
                return code
    return ""


def _fmt(r):
    return {
        "id": r["id"], "file_name": r["file_name"], "file_size": r["file_size"], "file_ext": r["file_ext"],
        "category": r["category"], "category_name": CATEGORY_NAMES.get(r["category"], "未归类"),
        "menu_code": r["menu_code"], "villager_name": r["villager_name"], "related_id": r["related_id"],
        "upload_user": r["upload_user"], "upload_time": r["upload_time"], "url": f"/api/files/{r['file_path']}",
    }


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...), user: dict = Depends(require_roles(*WRITABLE)), request: Request = None):
    now = datetime.now()
    date_dir = now.strftime("%Y%m%d")
    save_dir = os.path.join(UPLOAD_DIR, "archive", date_dir)
    os.makedirs(save_dir, exist_ok=True)
    result = []
    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in ALLOW_EXT:
            continue
        name = f"{now.strftime('%H%M%S')}_{os.urandom(4).hex()}{ext}"
        rel = os.path.join("archive", date_dir, name)
        path = os.path.join(save_dir, name)
        with open(path, "wb") as out:
            shutil.copyfileobj(f.file, out)
        size = os.path.getsize(path)
        category = auto_classify(f.filename or "")
        if category:
            lg = query_one("SELECT name FROM sys_menu_config WHERE code=?", (category,))
        else:
            lg = None
        with get_db() as db:
            cur = db.execute(
                "INSERT INTO t_file_archive(file_name,file_path,file_size,file_ext,category,menu_code,villager_name,related_id,upload_user,upload_time) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (f.filename, rel, size, ext, category or None, category or None, None, None, user["username"], now.strftime("%Y-%m-%d %H:%M:%S")),
            )
            new_id = cur.lastrowid
        result.append({
            "id": new_id, "file_name": f.filename, "category": category,
            "category_name": CATEGORY_NAMES.get(category, "未归类"), "size": size,
        })
    log_operation(user, "上传文档", "文档归档", f"批量上传 {len(result)} 个文件", get_client_ip(request))
    await notify_data_changed(module="archive")
    return {"message": f"上传完成 {len(result)} 个文件", "items": result}


@router.get("")
def list_archive(page: int = 1, size: int = 12, category: str = "", keyword: str = "",
                 user: dict = Depends(get_current_user)):
    where, params = ["1=1"], []
    if category:
        where.append("category=?")
        params.append(category)
    if keyword:
        where.append("(file_name LIKE ? OR villager_name LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql = " WHERE " + " AND ".join(where)
    total = query_one(f"SELECT COUNT(*) c FROM t_file_archive{sql}", params)["c"]
    rows = query_all(f"SELECT * FROM t_file_archive{sql} ORDER BY id DESC LIMIT ? OFFSET ?", params + [size, (page - 1) * size])
    return {"total": total, "page": page, "size": size, "list": [_fmt(r) for r in rows]}


class RelateBody(BaseModel):
    menu_code: str
    villager_name: str
    related_id: int = None


@router.post("/{file_id}/relate")
async def relate_file(file_id: int, body: RelateBody, user: dict = Depends(require_roles(*WRITABLE)), request: Request = None):
    f = query_one("SELECT * FROM t_file_archive WHERE id=?", (file_id,))
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    execute("UPDATE t_file_archive SET menu_code=?,villager_name=?,related_id=? WHERE id=?",
            (body.menu_code, body.villager_name, body.related_id, file_id))
    log_operation(user, "档案关联", "文档归档", f"文件[{f['file_name']}]关联到[{body.villager_name}]", get_client_ip(request))
    await notify_data_changed(module="archive")
    return {"message": "关联成功"}


@router.post("/{file_id}/classify")
async def classify_file(file_id: int, body: RelateBody, user: dict = Depends(require_roles(*WRITABLE)), request: Request = None):
    f = query_one("SELECT * FROM t_file_archive WHERE id=?", (file_id,))
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    execute("UPDATE t_file_archive SET menu_code=?,category=? WHERE id=?", (body.menu_code, body.menu_code, file_id))
    log_operation(user, "档案归类", "文档归档", f"文件[{f['file_name']}]归类到[{CATEGORY_NAMES.get(body.menu_code,'')}]", get_client_ip(request))
    await notify_data_changed(module="archive")
    return {"message": "归类成功"}


@router.get("/categories")
def categories(user: dict = Depends(get_current_user)):
    return [{"code": k, "name": v} for k, v in CATEGORY_NAMES.items()]


@router.get("/download/{file_id}")
def download_file(file_id: int, user: dict = Depends(get_current_user)):
    f = query_one("SELECT * FROM t_file_archive WHERE id=?", (file_id,))
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    path = os.path.join(UPLOAD_DIR, f["file_path"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="物理文件已丢失")
    return FileResponse(path, filename=f["file_name"])


@router.delete("/{file_id}")
async def delete_file(file_id: int, user: dict = Depends(require_roles(*WRITABLE)), request: Request = None):
    f = query_one("SELECT * FROM t_file_archive WHERE id=?", (file_id,))
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    execute("DELETE FROM t_file_archive WHERE id=?", (file_id,))
    log_operation(user, "删除文档", "文档归档", f"删除文件[{f['file_name']}]", get_client_ip(request))
    await notify_data_changed(module="archive")
    return {"message": "删除成功"}


@router.post("/scan")
async def scan_classify(user: dict = Depends(require_roles(*WRITABLE)), request: Request = None):
    rows = query_all("SELECT * FROM t_file_archive WHERE category IS NULL OR category=''")
    updated = 0
    for r in rows:
        cat = auto_classify(r["file_name"])
        if cat:
            execute("UPDATE t_file_archive SET menu_code=?,category=? WHERE id=?", (cat, cat, r["id"]))
            updated += 1
    log_operation(user, "智能归类", "文档归档", f"自动归类 {updated} 个文件", get_client_ip(request))
    await notify_data_changed(module="archive")
    return {"message": f"智能归类完成：{updated} 个文件已匹配归类"}


@router.post("/{file_id}/ocr")
async def ocr_recognize(file_id: int, user: dict = Depends(require_roles(*WRITABLE)), request: Request = None):
    """图片证件 OCR 识别（生产环境安装 PaddleOCR 后启用，此处返回结构化占位结果）"""
    f = query_one("SELECT * FROM t_file_archive WHERE id=?", (file_id,))
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    ext = (f["file_ext"] or "").lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        raise HTTPException(status_code=400, detail="仅支持图片证件识别")
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        result = ocr.ocr(os.path.join(UPLOAD_DIR, f["file_path"]), cls=True)
        texts = []
        for line in result or []:
            for box in line or []:
                texts.append(box[1][0])
        return {"available": True, "text": "\n".join(texts)}
    except ImportError:
        return {"available": False, "message": "当前环境未安装 PaddleOCR，部署包内可启用。系统将自动提取身份证号并回填台账。"}
