"""低保信息台账字段规格迁移：调整为需求规格的 20 个数据字段 + 序号/创建时间/操作。

- 新增：户主姓名、性别、年龄、是否残疾、残疾类型、残疾等级、低保类型、救助类型、开户行、社保卡号、动态调整记录
- 调整标签：身份证号→身份证号码、联系电话→联系方式、开始时间、保障标准（元/月）
- 创建时间列：加入字段配置并在列表展示
- 辅助保留：结束时间、状态（列表隐藏、表单保留，维持业务完整性）
- 按需求顺序重排；幂等，可重复执行
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import get_conn, ensure_column, SQLITE_TYPE_MAP, dumps

MENU = "low_income"
TABLE = "t_low_income"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

NEW_FIELDS = [
    ("householder",   "户主姓名",     "text",   0, 1, 1, None),
    ("gender",        "性别",        "select", 0, 1, 1, ["男", "女"]),
    ("age",           "年龄",        "number", 0, 1, 1, None),
    ("is_disabled",   "是否残疾",     "select", 0, 1, 1, ["是", "否"]),
    ("disability_type", "残疾类型",   "select", 0, 1, 1, ["视力", "听力", "言语", "肢体", "智力", "精神", "多重"]),
    ("disability_level", "残疾等级",  "select", 0, 1, 1, ["一级", "二级", "三级", "四级"]),
    ("low_income_type", "低保类型",   "select", 0, 1, 1, ["城市低保", "农村低保"]),
    ("relief_type",   "救助类型",     "select", 0, 1, 1, ["临时救助", "医疗救助", "教育救助", "住房救助", "就业救助", "其他"]),
    ("bank",          "开户行",       "text",   0, 1, 1, None),
    ("social_card",   "社保卡号",      "text",   0, 1, 1, None),
    ("adjust_record", "动态调整记录",  "text",   0, 1, 1, None),
]

# 最终顺序（需求 20 个数据字段；序号、操作为前端列）
ORDER = ["village_group", "household_no", "householder", "name", "gender", "id_card",
         "age", "is_disabled", "disability_type", "disability_level", "low_income_type",
         "phone", "start_date", "monthly_amount", "relief_type", "bank", "social_card",
         "adjust_record", "remark", "create_time"]

RENAME = {"id_card": "身份证号码", "phone": "联系方式", "start_date": "开始时间",
          "monthly_amount": "保障标准（元/月）"}

# 辅助字段：列表隐藏、表单保留
FORM_ONLY = {"end_date", "status"}


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
    # 辅助字段：列表隐藏、表单保留
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
                (1, "admin", "台账字段规格调整", "字段配置", "低保信息台账字段调整为新规格（22列）", "127.0.0.1", NOW))
    conn.commit()
    conn.close()
    print("迁移完成：低保信息台账字段已调整为新规格")


if __name__ == "__main__":
    main()
