from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth import get_current_user, require_roles, get_client_ip
from ..config import ROLE_ADMIN
from ..database import query_all, query_one, execute
from ..services.audit import log_operation
from ..services.sync import notify_data_changed

router = APIRouter(prefix="/api/menus", tags=["menus"])


class MenuBody(BaseModel):
    code: str = None
    name: str = None
    icon: str = ""
    sort_order: int = 0
    is_visible: int = 1
    path: str = None
    parent_code: str = None
    table_name: str = None
    is_ledger: int = 0


def _tree(menus):
    roots = []
    children_map = {}
    for m in menus:
        m = dict(m)
        m["children"] = []
        children_map.setdefault(m["parent_code"], []).append(m)
    def build(parent):
        for m in sorted(children_map.get(parent, []), key=lambda x: x["sort_order"]):
            m["children"] = build(m["code"])
            yield m
    return list(build(None))


@router.get("/tree")
async def menu_tree(user: dict = Depends(get_current_user)):
    menus = query_all("SELECT * FROM sys_menu_config ORDER BY sort_order,id")
    return _tree(menus)


@router.get("")
async def menu_list(user: dict = Depends(get_current_user)):
    if user["role"] == ROLE_ADMIN:
        rows = query_all("SELECT * FROM sys_menu_config ORDER BY sort_order,id")
    else:
        rows = query_all(
            "SELECT * FROM sys_menu_config WHERE is_visible=1 AND (parent_code IS NULL OR parent_code NOT IN ('system')) ORDER BY sort_order,id"
        )
    return rows


@router.post("")
async def create_menu(body: MenuBody, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    if not body.code or not body.name:
        raise HTTPException(status_code=400, detail="菜单编码和名称必填")
    if query_one("SELECT id FROM sys_menu_config WHERE code=?", (body.code,)):
        raise HTTPException(status_code=400, detail="菜单编码已存在")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute(
        "INSERT INTO sys_menu_config(code,name,parent_code,sort_order,is_visible,is_ledger,table_name,path,create_time) VALUES(?,?,?,?,?,?,?,?,?)",
        (body.code, body.name, body.parent_code, body.sort_order, body.is_visible, body.is_ledger, body.table_name, body.path, now),
    )
    # 台账类新菜单自动初始化字段配置：从字段库复制 default_visible=1 的系统字段
    if body.is_ledger:
        now2 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        library = query_all("SELECT * FROM sys_field_library WHERE default_visible=1 ORDER BY id")
        for idx, f in enumerate(library):
            execute(
                "INSERT INTO sys_field_config(menu_code,physical_field,display_label,data_type,form_component,is_system,show_in_list,show_in_form,is_required,sort_order,is_deleted,options_json,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (body.code, f["name"], f["label"], f["data_type"], f["form_component"],
                 1, 1, 1, 0, idx + 1, 0, f["options_json"], now2, now2),
            )
    log_operation(user, "新增菜单", "菜单配置", f"新增菜单 {body.code} {body.name}", get_client_ip(request))
    await notify_data_changed(module="menu")
    return {"message": "创建成功"}


@router.put("/{code}")
async def update_menu(code: str, body: MenuBody, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    m = query_one("SELECT * FROM sys_menu_config WHERE code=?", (code,))
    if not m:
        raise HTTPException(status_code=404, detail="菜单不存在")
    execute("UPDATE sys_menu_config SET name=?,sort_order=?,is_visible=?,path=? WHERE code=?",
            (body.name, body.sort_order, body.is_visible, body.path, code))
    log_operation(user, "修改菜单", "菜单配置", f"修改菜单 {code}", get_client_ip(request))
    await notify_data_changed(module="menu")
    return {"message": "修改成功"}


@router.delete("/{code}")
async def delete_menu(code: str, user: dict = Depends(require_roles(ROLE_ADMIN)), request: Request = None):
    m = query_one("SELECT * FROM sys_menu_config WHERE code=?", (code,))
    if not m:
        raise HTTPException(status_code=404, detail="菜单不存在")
    if query_one("SELECT id FROM sys_menu_config WHERE parent_code=?", (code,)):
        raise HTTPException(status_code=400, detail="存在子菜单，不能删除")
    if m["is_ledger"] == 1 and query_one("SELECT id FROM sys_field_config WHERE menu_code=? AND is_deleted=0", (code,)):
        pass  # 台账菜单保留字段配置
    execute("DELETE FROM sys_menu_config WHERE code=?", (code,))
    log_operation(user, "删除菜单", "菜单配置", f"删除菜单 {code}", get_client_ip(request))
    await notify_data_changed(module="menu")
    return {"message": "删除成功"}
