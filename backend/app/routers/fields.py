import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth import get_current_user, require_roles, get_client_ip
from ..config import ROLE_ADMIN, ROLE_MANAGER
from ..database import get_db, query_all, query_one, execute, dumps, loads, ensure_column, SQLITE_TYPE_MAP
from ..services.audit import log_operation
from ..services.sync import notify_data_changed

router = APIRouter(prefix="/api/fields", tags=["fields"])

VALID_TYPES = ["text", "number", "date", "datetime", "image", "select", "boolean", "textarea"]
VALID_COMPONENTS = {"text": "input", "number": "number", "date": "date", "datetime": "datetime",
                    "image": "upload", "select": "select", "boolean": "switch", "textarea": "textarea"}

try:
    from pypinyin import lazy_pinyin
    _HAS_PINYIN = True
except Exception:  # 离线环境无 pypinyin 时回退编号方案
    _HAS_PINYIN = False


def _pinyin_code(text):
    """中文/混合文本转英文编码：全拼小写，非字母数字转下划线，去重下划线。无有效拼音时返回 None"""
    if not _HAS_PINYIN:
        return None
    parts = lazy_pinyin(text, errors=lambda x: x)
    raw = "_".join(parts)
    code = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    code = re.sub(r"_+", "_", code)
    if len(code) > 50:
        code = code[:50].rstrip("_")
    return code or None


def _unique_code(menu_code, base):
    """同台账内保证编码唯一：冲突时追加 _2/_3..."""
    if not base:
        return None
    exist = {r["physical_field"] for r in query_all(
        "SELECT physical_field FROM sys_field_config WHERE menu_code=?", (menu_code,))}
    if base not in exist:
        return base
    idx = 2
    while f"{base}_{idx}" in exist:
        idx += 1
    return f"{base}_{idx}"

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
    props: dict = None
    sort_order: int = 0


class SimpleFieldBody(BaseModel):
    display_label: str = None
    data_type: str = None
    options: list = None
    code: str = None
    tips: str = None


def _menu_info(menu_code):
    m = query_one("SELECT * FROM sys_menu_config WHERE code=?", (menu_code,))
    if not m or m["is_ledger"] != 1:
        raise HTTPException(status_code=404, detail="台账不存在")
    return m


def _fmt(f):
    try:
        props = loads(f["props_json"] if f["props_json"] else None, {})
    except Exception:
        props = {}
    return {
        "id": f["id"], "menu_code": f["menu_code"], "physical_field": f["physical_field"],
        "display_label": f["display_label"], "data_type": f["data_type"],
        "form_component": f["form_component"], "is_system": f["is_system"],
        "show_in_list": f["show_in_list"], "show_in_form": f["show_in_form"],
        "is_required": f["is_required"], "sort_order": f["sort_order"],
        "is_deleted": f["is_deleted"], "options": loads(f["options_json"], []),
        "props": props,
    }


def _create_field_impl(menu_code, table_name, display_label, data_type, options, show_in_list, show_in_form,
                       is_required, sort, physical, props=None):
    """事务化创建字段：建物理列 + 写配置，物理列名由调用方决定(存量 ext_{seq} / 简化模式拼音)"""
    with get_db() as db:
        ensure_column(db, table_name, physical, SQLITE_TYPE_MAP[data_type])
        db.execute(
            "INSERT INTO sys_field_config(menu_code,physical_field,display_label,data_type,form_component,is_system,show_in_list,show_in_form,is_required,sort_order,is_deleted,options_json,props_json,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (menu_code, physical, display_label, data_type, VALID_COMPONENTS[data_type], 0,
             show_in_list, show_in_form, is_required, sort, 0,
             dumps(options) if options else None,
             dumps(props) if props else None,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


@router.get("/{menu_code}")
def list_fields(menu_code: str, user: dict = Depends(get_current_user)):
    _menu_info(menu_code)
    rows = query_all("SELECT * FROM sys_field_config WHERE menu_code=? AND is_deleted=0 ORDER BY sort_order,id", (menu_code,))
    return [_fmt(r) for r in rows]


@router.get("/{menu_code}/recycle")
def recycle_fields(menu_code: str, user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER))):
    _menu_info(menu_code)
    rows = query_all("SELECT * FROM sys_field_config WHERE menu_code=? AND is_deleted=1 ORDER BY id DESC", (menu_code,))
    return [_fmt(r) for r in rows]


@router.post("/{menu_code}")
async def create_field(menu_code: str, body: FieldBody, user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)), request: Request = None):
    m = _menu_info(menu_code)
    if not body.display_label:
        raise HTTPException(status_code=400, detail="字段名称必填")
    if body.data_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="字段类型不合法")
    if query_one("SELECT id FROM sys_field_config WHERE menu_code=? AND display_label=? AND is_deleted=0",
                 (menu_code, body.display_label.strip())):
        raise HTTPException(status_code=400, detail="该字段名称已添加到当前台账")
    # 引用检查：物理列名
    max_row = query_one("SELECT MAX(sort_order) s FROM sys_field_config WHERE menu_code=? AND is_deleted=0", (menu_code,))
    sort = (max_row["s"] or 0) + 1
    seq = query_one("SELECT COUNT(*) c FROM sys_field_config WHERE menu_code=?", (menu_code,))["c"] + 1
    physical = f"ext_{seq}"
    _create_field_impl(menu_code, m["table_name"], body.display_label, body.data_type, body.options,
                       body.show_in_list, body.show_in_form, body.is_required, sort, physical, body.props)
    log_operation(user, "新增字段", "字段配置", f"台账[{m['name']}]新增字段 {body.display_label}", get_client_ip(request))
    await notify_data_changed(menu_code, "field")
    return {"message": "字段创建成功", "physical_field": physical}


@router.post("/{menu_code}/simple")
async def create_simple_field(menu_code: str, body: SimpleFieldBody,
                              user: dict = Depends(get_current_user), request: Request = None):
    """简化模式：仅填显示名称+类型，系统自动生成英文编码与排序号"""
    m = _menu_info(menu_code)
    if not body.display_label:
        raise HTTPException(status_code=400, detail="字段名称必填")
    if body.data_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="字段类型不合法")
    if query_one("SELECT id FROM sys_field_config WHERE menu_code=? AND display_label=? AND is_deleted=0",
                 (menu_code, body.display_label.strip())):
        raise HTTPException(status_code=400, detail="该字段名称已添加到当前台账")
    max_row = query_one("SELECT MAX(sort_order) s FROM sys_field_config WHERE menu_code=? AND is_deleted=0", (menu_code,))
    sort = (max_row["s"] or 0) + 1
    seq = query_one("SELECT COUNT(*) c FROM sys_field_config WHERE menu_code=?", (menu_code,))["c"] + 1
    manual = (body.code or "").strip().lower()
    if manual:
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", manual):
            raise HTTPException(status_code=400, detail="字段编码仅支持小写字母、数字、下划线，以字母开头，长度2-64")
        if query_one("SELECT id FROM sys_field_config WHERE menu_code=? AND physical_field=? AND is_deleted=0",
                     (menu_code, manual)):
            raise HTTPException(status_code=400, detail="字段编码已存在，请更换")
        physical = manual
    else:
        physical = _unique_code(menu_code, _pinyin_code(body.display_label)) or f"ext_{seq}"
    props = {"tips": body.tips} if body.tips else None
    _create_field_impl(menu_code, m["table_name"], body.display_label, body.data_type, body.options,
                       1, 1, 0, sort, physical, props)
    log_operation(user, "新增字段", "字段配置", f"台账[{m['name']}]简化新增字段 {body.display_label}（{physical}）", get_client_ip(request))
    await notify_data_changed(menu_code, "field")
    return {"message": "字段创建成功", "physical_field": physical}


@router.get("/{menu_code}/code-suggest")
def field_code_suggest(menu_code: str, label: str = "", user: dict = Depends(get_current_user)):
    """编码自动生成建议：供前端实时预览，无权限限制"""
    _menu_info(menu_code)
    base = _pinyin_code(label) if label else None
    if not base:
        return {"suggest": "", "note": "无法自动生成英文编码，将使用编号方案"}
    return {"suggest": _unique_code(menu_code, base)}


@router.put("/{field_id}")
async def update_field(field_id: int, body: FieldBody, user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)), request: Request = None):
    f = query_one("SELECT * FROM sys_field_config WHERE id=?", (field_id,))
    if not f:
        raise HTTPException(status_code=404, detail="字段不存在")
    m = _menu_info(f["menu_code"])
    # 系统内置字段：类型与编码锁定，禁止变更
    if f["is_system"] == 1 and body.data_type and body.data_type != f["data_type"]:
        raise HTTPException(status_code=400, detail="系统内置字段类型锁定保护，禁止变更")
    if body.data_type and body.data_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="字段类型不合法")
    if body.data_type and body.data_type != f["data_type"] and f["is_system"] == 0:
        # 自定义字段类型修改：更新配置层与组件映射，物理列由 SQLite 动态类型兼容
        execute("UPDATE sys_field_config SET data_type=?,form_component=? WHERE id=?",
                (body.data_type, VALID_COMPONENTS[body.data_type], field_id))
    is_required = body.is_required if body.is_required is not None else f["is_required"]
    show_in_form = body.show_in_form if body.show_in_form is not None else f["show_in_form"]
    # 必填字段不可隐藏（表单展示锁定）
    if is_required == 1 and show_in_form == 0:
        raise HTTPException(status_code=400, detail="必填字段不可在录入表单中隐藏")
    if body.props is not None and not isinstance(body.props, dict):
        raise HTTPException(status_code=400, detail="校验规则格式不合法")
    execute(
        "UPDATE sys_field_config SET display_label=?,show_in_list=?,show_in_form=?,is_required=?,sort_order=?,options_json=?,props_json=?,update_time=? WHERE id=?",
        (body.display_label or f["display_label"], body.show_in_list, show_in_form, is_required,
         body.sort_order if body.sort_order else f["sort_order"],
         dumps(body.options) if body.options is not None else f["options_json"],
         dumps(body.props) if body.props is not None else f["props_json"],
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), field_id),
    )
    log_operation(user, "修改字段", "字段配置", f"台账[{m['name']}]修改字段 {f['physical_field']}", get_client_ip(request))
    await notify_data_changed(f["menu_code"], "field")
    return {"message": "修改成功"}


@router.delete("/{field_id}")
async def delete_field(field_id: int, user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)), request: Request = None):
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
async def restore_field(field_id: int, user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)), request: Request = None):
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
async def sort_fields(menu_code: str, body: SortBody, user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)), request: Request = None):
    _menu_info(menu_code)
    with get_db() as db:
        for idx, fid in enumerate(body.order):
            db.execute("UPDATE sys_field_config SET sort_order=?,update_time=? WHERE id=?", (idx + 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fid))
    log_operation(user, "字段排序", "字段配置", f"台账[{menu_code}]调整字段排序", get_client_ip(request))
    await notify_data_changed(menu_code, "field")
    return {"message": "排序已保存"}


@router.get("/library/list")
def field_library(category: str = "", keyword: str = "", field_type: str = "",
                  user: dict = Depends(get_current_user)):
    sql = "SELECT * FROM sys_field_library"
    where, params = [], []
    if category:
        where.append("category=?")
        params.append(category)
    if keyword:
        where.append("(label LIKE ? OR name LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%"]
    if field_type:
        where.append("data_type=?")
        params.append(field_type)
    if where:
        sql += " WHERE " + " AND ".join(where)
    rows = query_all(sql + " ORDER BY id", params)
    return [{"id": r["id"], "name": r["name"], "label": r["label"], "data_type": r["data_type"],
             "form_component": r["form_component"], "options": loads(r["options_json"], []),
             "category": r["category"]} for r in rows]


@router.get("/library/categories")
def field_library_categories(user: dict = Depends(get_current_user)):
    rows = query_all("SELECT name FROM sys_field_category ORDER BY sort_order,id")
    return [r["name"] for r in rows]


class CategoryBody(BaseModel):
    name: str = None


@router.post("/library/categories")
def create_category(body: CategoryBody, user: dict = Depends(require_roles(ROLE_ADMIN))):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="分类名称不能为空")
    if len(name) > 20:
        raise HTTPException(status_code=400, detail="分类名称过长（最多20字）")
    if query_one("SELECT id FROM sys_field_category WHERE name=?", (name,)):
        raise HTTPException(status_code=400, detail="分类已存在")
    max_sort = query_one("SELECT MAX(sort_order) s FROM sys_field_category")
    execute("INSERT INTO sys_field_category(name,sort_order,create_time) VALUES(?,?,?)",
            (name, (max_sort["s"] or 0) + 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    return {"message": "分类已创建"}


@router.put("/library/categories/{old_name}")
def rename_category(old_name: str, body: CategoryBody, user: dict = Depends(require_roles(ROLE_ADMIN))):
    name = (body.name or "").strip()
    if not name or len(name) > 20:
        raise HTTPException(status_code=400, detail="分类名称不合法")
    if not query_one("SELECT id FROM sys_field_category WHERE name=?", (old_name,)):
        raise HTTPException(status_code=404, detail="分类不存在")
    if query_one("SELECT id FROM sys_field_category WHERE name=?", (name,)):
        raise HTTPException(status_code=400, detail="分类已存在")
    with get_db() as db:
        db.execute("UPDATE sys_field_category SET name=? WHERE name=?", (name, old_name))
        db.execute("UPDATE sys_field_library SET category=? WHERE category=?", (name, old_name))
    return {"message": "分类已重命名"}


@router.delete("/library/categories/{name}")
def delete_category(name: str, user: dict = Depends(require_roles(ROLE_ADMIN))):
    if not query_one("SELECT id FROM sys_field_category WHERE name=?", (name,)):
        raise HTTPException(status_code=404, detail="分类不存在")
    cnt = query_one("SELECT COUNT(*) c FROM sys_field_library WHERE category=?", (name,))["c"]
    if cnt > 0:
        raise HTTPException(status_code=400, detail=f"该分类下还有 {cnt} 个字段，请先移出或删除字段")
    execute("DELETE FROM sys_field_category WHERE name=?", (name,))
    return {"message": "分类已删除"}
