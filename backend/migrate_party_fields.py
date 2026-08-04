"""党员信息台账字段规格迁移：调整为需求规格的 15 个数据字段 + 序号/创建时间/操作。

- 新增：户号、户主姓名、年龄、党龄、务工地址、党费（元/年）
- 调整标签：身份证号→身份证号码、联系电话→联系方式、入党日期→入党时间、转正日期→转正时间
- 创建时间列：加入字段配置并在列表展示
- 隐藏保留（不删数据）：所在支部（列表/表单隐藏）
- 辅助保留：党费收缴状态（列表隐藏、表单保留，维持党费欠缴预警引擎）
- 按需求顺序重排；幂等，可重复执行
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import get_conn, ensure_column, SQLITE_TYPE_MAP, dumps

MENU = "party_member"
TABLE = "t_party_member"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

NEW_FIELDS = [
    ("household_no", "户号",       "text",   0, 1, 1, None),
    ("householder",  "户主姓名",    "text",   0, 1, 1, None),
    ("age",          "年龄",       "number", 0, 1, 1, None),
    ("party_age",    "党龄",       "number", 0, 1, 1, None),
    ("work_address", "务工地址",    "text",   0, 1, 1, None),
    ("fee_amount",   "党费（元/年）", "number", 0, 1, 1, None),
]

# 最终顺序（需求 15 个数据字段；序号、操作为前端列）
ORDER = ["village_group", "household_no", "householder", "name", "gender", "id_card",
         "age", "join_date", "positive_date", "party_age", "phone", "work_address",
         "fee_amount", "remark", "create_time"]

RENAME = {"id_card": "身份证号码", "phone": "联系方式", "join_date": "入党时间", "positive_date": "转正时间"}

# 隐藏保留（保留数据，仅前端不展示）
HIDE = {"party_branch"}
# 辅助字段：列表隐藏、表单保留（维持党费欠缴预警）
FORM_ONLY = {"fee_status"}


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
            cur.execute(
                "INSERT INTO sys_field_config(menu_code,physical_field,display_label,data_type,form_component,is_system,show_in_list,show_in_form,is_required,sort_order,is_deleted,options_json,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (MENU, pf, label, ftype, "number" if ftype == "number" else ("select" if ftype == "select" else ("upload" if ftype == "image" else ("date" if ftype == "date" else "input"))),
                 1, lst, form, req, 0, 0, dumps(opts) if opts else None, NOW, NOW))
    # 创建时间列：加入字段配置并列表展示
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
    # 隐藏保留字段
    for pf in HIDE:
        cur.execute("UPDATE sys_field_config SET show_in_list=0,show_in_form=0,update_time=? WHERE menu_code=? AND physical_field=?",
                    (NOW, MENU, pf))
    # 辅助字段：列表隐藏、表单保留
    for pf in FORM_ONLY:
        cur.execute("UPDATE sys_field_config SET show_in_list=0,show_in_form=1,update_time=? WHERE menu_code=? AND physical_field=?",
                    (NOW, MENU, pf))
    # 排序（未列入 ORDER 的辅助字段排末尾）
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
                (1, "admin", "台账字段规格调整", "字段配置", "党员信息台账字段调整为新规格（17列）", "127.0.0.1", NOW))
    conn.commit()
    conn.close()
    print("迁移完成：党员信息台账字段已调整为新规格")


if __name__ == "__main__":
    main()
