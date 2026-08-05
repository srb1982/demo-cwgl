# -*- coding: utf-8 -*-
"""三费收缴台账：医疗保险/养老保险/大病补充 由下拉改为金额（number）。

- 字段配置：data_type=number, form_component=number, options_json 清空
- 存量数据：已缴 -> 对应默认金额，未缴/减免 -> 0
- 幂等：重复执行不报错
"""
import sqlite3
import sys
from datetime import datetime

DB = "data/village.db"
MENU = "fee_collect"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

AMOUNTS = {
    "medical_status": 380,      # 医疗保险（元/年）
    "pension_status": 300,      # 养老保险（元/年）
    "supplement_status": 40,    # 大病补充（元/年）
}

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("SELECT 1 FROM sys_config WHERE config_key='db_version_fee_amount'")
if cur.fetchone():
    print("已迁移过（fee_amount），跳过")
    sys.exit(0)

for field, amount in AMOUNTS.items():
    cur.execute(
        """UPDATE sys_field_config SET data_type='number', form_component='number',
           options_json=NULL, update_time=? WHERE menu_code=? AND physical_field=?""",
        (NOW, MENU, field),
    )
    cur.execute(
        f"UPDATE t_fee_collect SET {field}=CASE {field} WHEN '已缴' THEN ? WHEN '减免' THEN 0 ELSE 0 END",
        (amount,),
    )

cur.execute(
    """INSERT INTO sys_oper_log(username,action,module,detail,create_time)
       VALUES('admin','台账字段规格调整','字段配置','三费收缴台账：医疗保险/养老保险/大病补充改为金额输入',?)""",
    (NOW,),
)
cur.execute(
    """INSERT INTO sys_config(config_key,config_value,remark)
       VALUES('db_version_fee_amount','done','三费收缴医疗保险/养老保险/大病补充改为金额类型')""",
)
conn.commit()
print("迁移完成：三费收缴医疗保险/养老保险/大病补充已改为金额类型")
conn.close()
