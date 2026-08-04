"""残疾人信息台账字段规格迁移：调整为需求规格的 18 个数据字段 + 序号/创建时间/操作。

- 新增：户号、户主姓名、性别、年龄、残疾证照片、是否低保、办证日期、换证日期、监护人、监护人电话
- 调整标签：身份证号→身份证号码、联系电话→联系方式、残疾类别→残疾类型
- 创建时间列：加入字段配置并在列表展示
- 隐藏保留（不删数据）：残疾证号（列表/表单隐藏）
- 辅助保留：证件到期日、证件状态（列表隐藏、表单保留，维持换证预警引擎）
- 按需求顺序重排；幂等，可重复执行
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import get_conn, ensure_column, SQLITE_TYPE_MAP, dumps

MENU = "disabled"
TABLE = "t_disabled"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

NEW_FIELDS = [
    ("household_no", "户号",       "text",   0, 1, 1, None),
    ("householder",  "户主姓名",    "text",   0, 1, 1, None),
    ("gender",       "性别",       "select", 0, 1, 1, ["男", "女"]),
    ("age",          "年龄",       "number", 0, 1, 1, None),
    ("disability_photo", "残疾证照片", "image", 0, 1, 1, None),
    ("low_income",   "是否低保",    "select", 0, 1, 1, ["是", "否"]),
    ("certificate_date", "办证日期", "date",  0, 1, 1, None),
    ("renew_date",   "换证日期",    "date",   0, 1, 1, None),
    ("guardian",     "监护人",     "text",   0, 1, 1, None),
    ("guardian_phone", "监护人电话", "text",  0, 1, 1, None),
]

# 最终顺序（需求 18 个数据字段；序号、操作为前端列）
ORDER = ["village_group", "household_no", "householder", "name", "gender", "id_card",
         "age", "disability_type", "disability_level", "disability_photo", "phone",
         "low_income", "certificate_date", "renew_date", "guardian", "guardian_phone",
         "remark", "create_time"]

RENAME = {"id_card": "身份证号码", "phone": "联系方式", "disability_type": "残疾类型"}

# 隐藏保留（保留数据，仅前端不展示）
HIDE = {"certificate_no"}
# 辅助字段：列表隐藏、表单保留（维持换证预警）
FORM_ONLY = {"expire_date", "cert_status"}


def main():
    conn = get_conn()
    cur = conn.cursor()
    for pf, label, ftype, req, lst, form, opts in NEW_FIELDS:
        ensure_column(cur, TABLE, pf, SQLITE_TYPE_MAP[ftype])
        row = cur.execute("SELECT id FROM sys_field_config WHERE menu_code=? AND physical_field=?", (MENU, pf)).fetchone()
        if row:
            cur.execute(
                "UPDATE sys_field_config SET display_label=?,data_type=?,is_required=?,show_in_list=?,show_in_form=?,is_deleted=0,options_json=?,update_time=? WHERE id=?",
                (label, ftype, req, lst, form, dumps(opts) if opts else None, NOW, row["id"]))
        else:
            comp = "number" if ftype == "number" else ("select" if ftype == "select" else ("upload" if ftype == "image" else ("date" if ftype == "date" else "input")))
            cur.execute(
                "INSERT INTO sys_field_config(menu_code,physical_field,display_label,data_type,form_component,is_system,show_in_list,show_in_form,is_required,sort_order,is_deleted,options_json,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (MENU, pf, label, ftype, comp, 1, lst, form, req, 0, 0, dumps(opts) if opts else None, NOW, NOW))
    # 创建时间列
    row = cur.execute("SELECT id FROM sys_field_config WHERE menu_code=? AND physical_field=?", (MENU, "create_time")).fetchone()
    if row:
        cur.execute("UPDATE sys_field_config SET display_label=?,show_in_list=1,show_in_form=0,is_deleted=0,update_time=? WHERE id=?",
                    ("创建时间", NOW, row["id"]))
    else:
        cur.execute(
            "INSERT INTO sys_field_config(menu_code,physical_field,display_label,data_type,form_component,is_system,show_in_list,show_in_form,is_required,sort_order,is_deleted,options_json,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (MENU, "create_time", "创建时间", "text", "input", 1, 1, 0, 0, 0, 0, None, NOW, NOW))
    # 标签调整
    for pf, label in RENAME.items():
        cur.execute("UPDATE sys_field_config SET display_label=?,update_time=? WHERE menu_code=? AND physical_field=?",
                    (label, NOW, MENU, pf))
    # 隐藏保留 / 辅助字段
    for pf in HIDE:
        cur.execute("UPDATE sys_field_config SET show_in_list=0,show_in_form=0,update_time=? WHERE menu_code=? AND physical_field=?",
                    (NOW, MENU, pf))
    for pf in FORM_ONLY:
        cur.execute("UPDATE sys_field_config SET show_in_list=0,show_in_form=1,update_time=? WHERE menu_code=? AND physical_field=?",
                    (NOW, MENU, pf))
    # 备注列表显示
    cur.execute("UPDATE sys_field_config SET show_in_list=1,display_label='备注',update_time=? WHERE menu_code=? AND physical_field=?",
                (NOW, MENU, "remark"))
    # 排序
    all_rows = cur.execute("SELECT id,physical_field FROM sys_field_config WHERE menu_code=? AND is_deleted=0", (MENU,)).fetchall()
    id_by_field = {r["physical_field"]: r["id"] for r in all_rows}
    tail = 90
    for pf, fid in id_by_field.items():
        if pf in ORDER:
            cur.execute("UPDATE sys_field_config SET sort_order=?,update_time=? WHERE id=?",
                        (ORDER.index(pf) + 1, NOW, fid))
        else:
            cur.execute("UPDATE sys_field_config SET sort_order=?,update_time=? WHERE id=?", (tail, NOW, fid))
            tail += 1
    # 审计日志
    cur.execute("INSERT INTO sys_oper_log(user_id,username,action,module,detail,ip,create_time) VALUES(?,?,?,?,?,?,?)",
                (1, "admin", "台账字段规格调整", "字段配置", "残疾人信息台账字段调整为新规格（20列）", "127.0.0.1", NOW))
    conn.commit()
    conn.close()
    print("迁移完成：残疾人信息台账字段已调整为新规格")


if __name__ == "__main__":
    main()
