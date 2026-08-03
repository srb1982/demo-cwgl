from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth import get_current_user, require_roles, get_client_ip
from ..config import ROLE_ADMIN
from ..database import get_db, query_all, query_one, execute, dumps, loads, ensure_column, SQLITE_TYPE_MAP
from ..services.audit import log_operation
from ..services.sync import notify_data_changed

router = APIRouter(prefix="/api/fields", tags=["fields"])

VALID_TYPES = ["text", "number", "date", "image", "select"]
VALID_COMPONENTS = {"text": "input", "number": "number", "date": "date", "image": "upload", "select": "select"}

# 被预警规则/大屏引用的内置字段，禁止删除
PROTECTED_FIELDS = {
    "disabled": ["expire_date", "cert_status"],
    "party_member": ["positive_date", "fee_status"],
    "elderly": ["expire_date", "subsidy_status"],
    "left_child": ["last_visit_date", "visit_status"],
    "village_public": ["expire_date", "status"],
    "project": ["contract_end", "payment_node", "progress"],
    "public_job": ["contract_end", "status"],
    "oversea": ["visa_expire_date", "return_date", "status"],
    "village_move": ["apply_date", "approve_status"],
    "visit_record": ["visit_date"],
}


class FieldBody(BaseModel):
    display_label: str = None
    data_type: str = None
    show_in_list: int = 1
    show_in_form: int = 1
    is_required: int = 0
    options: list = None
    sort_order: int = 0


def _menu_info(menu_code):
    m = query_one("SELECT * FROM sys_menu_config WHERE code=?", (menu_code,))
    if not m or m["is_ledger"] != 1:
        raise HTTPException(status_code=404, detail="台账不存在")
    return m


def _fmt(f):
    return {
        "id": f["id"], "menu_code": f["menu_code"], "physical_field": f["physical_field"],
        "display_label": f["display_label"], "data_type": f["data_type"],
        "form_component": f["form_component"], "is_system": f["is_system"],
        "show_in_list": f["show_in_list"], "show_in_form": f["show_in_form"],
        "is_required": f["is_required"], "sort_order": f["sort_order"],
        "is_deleted": f["is_deleted"], "options": loads(f["options_json"], []),
    }


@router.get("/{menu_code}")
def list_fields(menu_code: str, user: dict = Depends(get_current_user)):
    _menu_info(menu_code)
    rows = query_all("SELECT * FROM sys_field_config WHERE menu_code=? AND is_deleted=0 ORDER BY sort_order,id", (menu_code,))
    return [_fmt(r) for r in rows]


@router.get("/{menu_code}/recycle")
def recycle_fields(menu_code: str, user: dict = Depends(require_roles(ROLE_ADMIN))):
    _menu_info(menu_code)
    rows = query_all("SELECT * FROM sys_field_config WHERE menu_code=? AND is_deleted=1 ORDER BY id DESC", (menu_code,))
    return [_fmt(r) for r in rows]


@router.post("/{menu_code}")
async def create_field(menu_code: str, body: FieldBody, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    m = _menu_info(menu_code)
    if not body.display_label:
        raise HTTPException(status_code=400, detail="字段名称必填")
    if body.data_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="字段类型不合法")
    # 引用检查：物理列名
    max_row = query_one("SELECT MAX(sort_order) s FROM sys_field_config WHERE menu_code=? AND is_deleted=0", (menu_code,))
    sort = (max_row["s"] or 0) + 1
    seq = query_one("SELECT COUNT(*) c FROM sys_field_config WHERE menu_code=?", (menu_code,))["c"] + 1
    physical = f"ext_{seq}"
    with get_db() as db:
        ensure_column(db, m["table_name"], physical, SQLITE_TYPE_MAP[body.data_type])
        db.execute(
            "INSERT INTO sys_field_config(menu_code,physical_field,display_label,data_type,form_component,is_system,show_in_list,show_in_form,is_required,sort_order,is_deleted,options_json,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (menu_code, physical, body.display_label, body.data_type, VALID_COMPONENTS[body.data_type], 0,
             body.show_in_list, body.show_in_form, body.is_required, sort, 0,
             dumps(body.options) if body.options else None,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
    log_operation(user, "新增字段", "字段配置", f"台账[{m['name']}]新增字段 {body.display_label}", get_client_ip(request))
    await notify_data_changed(menu_code, "field")
    return {"message": "字段创建成功", "physical_field": physical}


@router.put("/{field_id}")
async def update_field(field_id: int, body: FieldBody, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    f = query_one("SELECT * FROM sys_field_config WHERE id=?", (field_id,))
    if not f:
        raise HTTPException(status_code=404, detail="字段不存在")
    m = _menu_info(f["menu_code"])
    execute(
        "UPDATE sys_field_config SET display_label=?,show_in_list=?,show_in_form=?,is_required=?,sort_order=?,options_json=?,update_time=? WHERE id=?",
        (body.display_label or f["display_label"], body.show_in_list, body.show_in_form, body.is_required,
         body.sort_order if body.sort_order else f["sort_order"],
         dumps(body.options) if body.options is not None else f["options_json"],
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), field_id),
    )
    log_operation(user, "修改字段", "字段配置", f"台账[{m['name']}]修改字段 {f['physical_field']}", get_client_ip(request))
    await notify_data_changed(f["menu_code"], "field")
    return {"message": "修改成功"}


@router.delete("/{field_id}")
async def delete_field(field_id: int, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    f = query_one("SELECT * FROM sys_field_config WHERE id=?", (field_id,))
    if not f:
        raise HTTPException(status_code=404, detail="字段不存在")
    if f["is_system"] == 1:
        raise HTTPException(status_code=400, detail="系统内置字段锁定保护，禁止删除")
    m = _menu_info(f["menu_code"])
    protected = PROTECTED_FIELDS.get(f["menu_code"], [])
    if f["physical_field"] in protected:
        raise HTTPException(status_code=400, detail="该字段被预警规则或数据大屏引用，禁止删除")
    execute("UPDATE sys_field_config SET is_deleted=1,update_time=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), field_id))
    log_operation(user, "删除字段", "字段配置", f"台账[{m['name']}]删除字段 {f['display_label']}（已入回收站）", get_client_ip(request))
    await notify_data_changed(f["menu_code"], "field")
    return {"message": "字段已移入回收站，历史数据保留"}


@router.post("/{field_id}/restore")
async def restore_field(field_id: int, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    f = query_one("SELECT * FROM sys_field_config WHERE id=?", (field_id,))
    if not f:
        raise HTTPException(status_code=404, detail="字段不存在")
    execute("UPDATE sys_field_config SET is_deleted=0,update_time=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), field_id))
    log_operation(user, "恢复字段", "字段配置", f"恢复字段 {f['display_label']}", get_client_ip(request))
    await notify_data_changed(f["menu_code"], "field")
    return {"message": "字段已恢复"}


class SortBody(BaseModel):
    order: list


@router.post("/{menu_code}/sort")
async def sort_fields(menu_code: str, body: SortBody, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    _menu_info(menu_code)
    with get_db() as db:
        for idx, fid in enumerate(body.order):
            db.execute("UPDATE sys_field_config SET sort_order=?,update_time=? WHERE id=?", (idx + 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fid))
    log_operation(user, "字段排序", "字段配置", f"台账[{menu_code}]调整字段排序", get_client_ip(request))
    await notify_data_changed(menu_code, "field")
    return {"message": "排序已保存"}


@router.get("/library/list")
def field_library(user: dict = Depends(require_roles(ROLE_ADMIN))):
    rows = query_all("SELECT * FROM sys_field_library")
    return [{"id": r["id"], "name": r["name"], "label": r["label"], "data_type": r["data_type"],
             "form_component": r["form_component"], "options": loads(r["options_json"], [])} for r in rows]
