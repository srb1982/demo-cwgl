"""水库移民台账字段规格迁移：调整为需求规格（16 个数据字段 + 序号/操作 = 18 列）。

- 新增：户号、人口、性别、民族、与户主关系、社保卡银行名称、开户姓名、社保卡号、
        是否死亡/公职人员、死亡时间/工作时间、创建时间
- 标签调整：村民组→组、身份证号→身份证号码
- 隐藏保留（不删数据）：移民编号、补助金额、迁移时间、安置地址（列表/表单不显示，可在字段配置恢复）
- 幂等，可重复执行
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import get_conn, ensure_column, SQLITE_TYPE_MAP, dumps

MENU = "reservoir_migrant"
TABLE = "t_reservoir_migrant"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

NEW_FIELDS = [
    ("household_no", "户号",            "text",   0, 1, 1, None),
    ("family_count", "人口",            "number", 0, 1, 1, None),
    ("gender",       "性别",            "select", 0, 1, 1, ["男", "女"]),
    ("ethnic",       "民族",            "select", 0, 1, 1, ["汉族", "壮族", "回族", "满族", "苗族", "维吾尔族", "彝族", "土家族", "蒙古族", "其他"]),
    ("relation",     "与户主关系",      "select", 0, 1, 1, ["本人", "配偶", "子女", "父母", "祖孙", "其他"]),
    ("bank_name",    "社保卡银行名称",  "text",   0, 1, 1, None),
    ("account_name", "开户姓名",        "text",   0, 1, 1, None),
    ("card_no",      "社保卡号",        "text",   0, 1, 1, None),
    ("is_deceased",  "是否死亡/公职人员", "select", 0, 1, 1, ["正常", "死亡", "公职人员"]),
    ("deceased_time", "死亡时间/工作时间", "date", 0, 1, 1, None),
    ("create_time",  "创建时间",        "text",   0, 1, 0, None),
]

# 最终顺序（需求 16 个数据字段 + 创建时间；序号、操作为前端列）
ORDER = ["village_group", "household_no", "family_count", "name", "gender", "ethnic",
         "relation", "id_card", "phone", "bank_name", "account_name", "card_no",
         "is_deceased", "deceased_time", "remark", "create_time"]

RENAME = {"village_group": "组", "id_card": "身份证号码"}

# 隐藏保留（不删数据）：列表/表单不显示，可后台恢复
HIDE = {"migrant_no", "subsidy_amount", "migrate_date", "address"}


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
            comp = "number" if ftype == "number" else ("select" if ftype == "select" else ("date" if ftype == "date" else "input"))
            is_sys = 1 if pf == "create_time" else 0
            cur.execute(
                "INSERT INTO sys_field_config(menu_code,physical_field,display_label,data_type,form_component,is_system,show_in_list,show_in_form,is_required,sort_order,is_deleted,options_json,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (MENU, pf, label, ftype, comp, is_sys, lst, form, req, 0, 0, dumps(opts) if opts else None, NOW, NOW))
    # 标签调整
    for pf, label in RENAME.items():
        cur.execute("UPDATE sys_field_config SET display_label=?,update_time=? WHERE menu_code=? AND physical_field=?",
                    (label, NOW, MENU, pf))
    # 备注列表显示
    cur.execute("UPDATE sys_field_config SET show_in_list=1,display_label='备注',update_time=? WHERE menu_code=? AND physical_field=?",
                (NOW, MENU, "remark"))
    # 隐藏保留旧字段
    for pf in HIDE:
        cur.execute("UPDATE sys_field_config SET show_in_list=0,show_in_form=0,update_time=? WHERE menu_code=? AND physical_field=?",
                    (NOW, MENU, pf))
    # 排序（未列入 ORDER 的字段排末尾）
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
                (1, "admin", "台账字段规格调整", "字段配置", "水库移民台账字段调整为新规格（18列）", "127.0.0.1", NOW))
    conn.commit()
    conn.close()
    print("迁移完成：水库移民台账字段已调整为新规格")


if __name__ == "__main__":
    main()
