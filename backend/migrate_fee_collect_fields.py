"""三费收缴台账字段规格迁移：调整为需求规格的 20 个数据字段 + 序号/操作。

- 新增：户号、人口数、户主姓名、与户主关系、年龄、身份标记、缴费方式、缴费时间、操作人、附件
- 调整标签：身份证号→身份证号码、联系电话→联系方式、缴费金额→家庭金额、收缴年度→缴费年度
- 附件：图片/文档通用上传（配合 upload-image 接口扩展）
- 按需求顺序重排；幂等，可重复执行
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import get_conn, ensure_column, SQLITE_TYPE_MAP, dumps

MENU = "fee_collect"
TABLE = "t_fee_collect"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

NEW_FIELDS = [
    ("household_no", "户号",       "text",   0, 1, 1, None),
    ("family_count", "人口数",      "number", 0, 1, 1, None),
    ("householder",  "户主姓名",    "text",   0, 1, 1, None),
    ("relation",     "与户主关系",  "select", 0, 1, 1, ["本人", "配偶", "子女", "父母", "祖孙", "其他"]),
    ("age",          "年龄",       "number", 0, 1, 1, None),
    ("identity_mark", "身份标记",   "select", 0, 1, 1, ["党员", "团员", "群众", "低保", "五保", "优抚对象", "村干部", "其他"]),
    ("pay_method",   "缴费方式",    "select", 0, 1, 1, ["微信", "支付宝", "现金", "银行代扣", "村集体代缴", "其他"]),
    ("pay_time",     "缴费时间",    "date",   0, 1, 1, None),
    ("operator",     "操作人",      "text",   0, 1, 1, None),
    ("attachment",   "附件",       "image",  0, 1, 1, None),
]

# 最终顺序（需求 20 个数据字段；序号、操作为前端列）
ORDER = ["village_group", "household_no", "family_count", "householder", "name", "relation",
         "id_card", "age", "identity_mark", "medical_status", "pension_status",
         "supplement_status", "amount", "phone", "pay_method", "pay_time", "operator",
         "fee_year", "attachment", "remark"]

RENAME = {"id_card": "身份证号码", "phone": "联系方式", "amount": "家庭金额", "fee_year": "缴费年度"}


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
    # 标签调整
    for pf, label in RENAME.items():
        cur.execute("UPDATE sys_field_config SET display_label=?,update_time=? WHERE menu_code=? AND physical_field=?",
                    (label, NOW, MENU, pf))
    # 备注列表显示
    cur.execute("UPDATE sys_field_config SET show_in_list=1,display_label='备注',update_time=? WHERE menu_code=? AND physical_field=?",
                (NOW, MENU, "remark"))
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
                (1, "admin", "台账字段规格调整", "字段配置", "三费收缴台账字段调整为新规格（22列）", "127.0.0.1", NOW))
    conn.commit()
    conn.close()
    print("迁移完成：三费收缴台账字段已调整为新规格")


if __name__ == "__main__":
    main()
