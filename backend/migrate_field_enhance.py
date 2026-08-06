# 增量迁移：sys_field_config 增加 props_json(校验规则)，sys_field_library 增加 category(分类)
import os
import sqlite3

DB = os.path.join(os.path.dirname(__file__), "data", "village.db")
db = sqlite3.connect(DB)

cols = {r[1] for r in db.execute("PRAGMA table_info(sys_field_config)")}
if "props_json" not in cols:
    db.execute("ALTER TABLE sys_field_config ADD COLUMN props_json TEXT")
    print("sys_field_config 已增加 props_json 列")

cols = {r[1] for r in db.execute("PRAGMA table_info(sys_field_library)")}
if "category" not in cols:
    db.execute("ALTER TABLE sys_field_library ADD COLUMN category TEXT")
    print("sys_field_library 已增加 category 列")

CATEGORIES = {
    "name": "基础信息",
    "gender": "基础信息",
    "birth_date": "基础信息",
    "address": "基础信息",
    "id_card": "身份与家庭",
    "household_no": "身份与家庭",
    "village_group": "身份与家庭",
    "phone": "联系方式",
    "status": "状态信息",
    "remark": "备注扩展",
}
for name, cat in CATEGORIES.items():
    db.execute("UPDATE sys_field_library SET category=? WHERE name=? AND (category IS NULL OR category='')", (cat, name))
print("字段库分类预置完成")

db.commit()
db.close()
