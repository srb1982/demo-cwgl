"""村民信息台账字段规格迁移：调整为需求规格的 19 个数据字段（序号、操作为前端列）。

- 新增：人口数、户主姓名、与户主关系、年龄、务工类型、务工地址、重点标识、文化程度、民族、状态
- 调整标签：身份证号→身份证号码、联系电话→联系方式、家庭住址→现居住地址
- 隐藏保留（不删数据）：出生日期、户籍类型、照片
- 软删除旧自定义字段 ext_12（文化程度，历史数据保留）
- 按需求顺序重排字段
- 幂等，可重复执行
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import get_conn, ensure_column, SQLITE_TYPE_MAP, dumps

MENU = "villager"
TABLE = "t_villager_info"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 需求字段规格（顺序即最终顺序；序号、操作为前端列，非数据字段）
NEW_FIELDS = [
    # physical, label, type, required, show_list, show_form, options
    ("population",   "人口数",   "number", 0, 1, 1, None),
    ("householder",  "户主姓名",  "text",   0, 1, 1, None),
    ("relation",     "与户主关系", "select", 0, 1, 1, ["本人", "配偶", "子女", "父母", "祖孙", "其他"]),
    ("age",          "年龄",     "number", 0, 1, 1, None),
    ("work_type",    "务工类型",  "select", 0, 1, 1, ["在家务农", "本地务工", "县外务工", "自主创业", "无"]),
    ("work_address", "务工地址",  "text",   0, 1, 1, None),
    ("key_mark",     "重点标识",  "select", 0, 1, 1, ["无", "低保", "残疾", "五保", "建档立卡", "优抚对象", "其他"]),
    ("education",    "文化程度",  "select", 0, 1, 1, ["文盲", "小学", "初中", "高中", "中专", "大专", "本科及以上"]),
    ("ethnic",       "民族",     "select", 0, 1, 1, ["汉族", "壮族", "回族", "满族", "苗族", "维吾尔族", "彝族", "土家族", "蒙古族", "其他"]),
    ("status",       "状态",     "select", 0, 1, 1, ["正常", "外出", "迁出", "死亡", "已注销"]),
]

# 最终顺序：现有字段名（不含隐藏字段与已删除字段）
ORDER = ["village_group", "household_no", "population", "householder", "name", "relation",
         "gender", "id_card", "age", "phone", "address", "work_type", "work_address",
         "key_mark", "education", "ethnic", "status", "remark"]

# 标签调整
RENAME = {"id_card": "身份证号码", "phone": "联系方式", "address": "现居住地址"}

# 隐藏保留（保留数据，仅前端不展示）
HIDE = {"birth_date", "household_type", "photo"}

# 软删除旧自定义字段
DROP_CUSTOM = {"ext_12"}


def main():
    conn = get_conn()
    cur = conn.cursor()
    # 新增物理列与字段配置
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
    # 标签调整
    for pf, label in RENAME.items():
        cur.execute("UPDATE sys_field_config SET display_label=?,update_time=? WHERE menu_code=? AND physical_field=?",
                    (label, NOW, MENU, pf))
    # 隐藏保留字段
    for pf in HIDE:
        cur.execute("UPDATE sys_field_config SET show_in_list=0,show_in_form=0,update_time=? WHERE menu_code=? AND physical_field=?",
                    (NOW, MENU, pf))
    # 软删除旧自定义字段
    for pf in DROP_CUSTOM:
        cur.execute("UPDATE sys_field_config SET is_deleted=1,update_time=? WHERE menu_code=? AND physical_field=?",
                    (NOW, MENU, pf))
    # 排序
    all_rows = cur.execute("SELECT id,physical_field FROM sys_field_config WHERE menu_code=? AND is_deleted=0", (MENU,)).fetchall()
    id_by_field = {r["physical_field"]: r["id"] for r in all_rows}
    tail = 90
    for pf, fid in id_by_field.items():
        if pf in ORDER:
            cur.execute("UPDATE sys_field_config SET sort_order=?,update_time=? WHERE id=?",
                        (ORDER.index(pf) + 1, NOW, fid))
        else:
            # 隐藏保留字段排到末尾，避免排序冲突
            cur.execute("UPDATE sys_field_config SET sort_order=?,update_time=? WHERE id=?", (tail, NOW, fid))
            tail += 1
    # 备注在列表中展示（需求含备注列）
    cur.execute("UPDATE sys_field_config SET show_in_list=1,update_time=? WHERE menu_code=? AND physical_field=?",
                (NOW, MENU, "remark"))
    # 审计日志
    cur.execute("INSERT INTO sys_oper_log(user_id,username,action,module,detail,ip,create_time) VALUES(?,?,?,?,?,?,?)",
                (1, "admin", "台账字段规格调整", "字段配置", "村民信息台账字段调整为新规格（19字段）", "127.0.0.1", NOW))
    conn.commit()
    conn.close()
    print("迁移完成：村民信息台账字段已调整为新规格")


if __name__ == "__main__":
    main()
