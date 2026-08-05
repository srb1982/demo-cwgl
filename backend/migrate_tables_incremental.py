"""台账字段增量迁移：15 个台账按需求规格补齐缺失字段（存量不动，只做增量）。

原则：
- 已有字段不删除，仅按需改名对齐需求；列表/表单不需要的旧字段隐藏保留（数据不丢，可在字段配置恢复）
- 缺失字段新建物理列并配置
- 需求含"创建时间"的台账补 create_time 列表列
- 移风易俗：新增"红事统计表"/"白事统计表"两个台账，原 custom_rural 菜单隐藏保留数据
- 幂等，可重复执行
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import get_conn, ensure_column, SQLITE_TYPE_MAP, dumps

NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 通用民族/关系/性别选项
ETHNIC = ["汉族", "壮族", "回族", "满族", "苗族", "维吾尔族", "彝族", "土家族", "蒙古族", "其他"]
RELATION = ["本人", "配偶", "子女", "父母", "祖孙", "其他"]
GENDER = ["男", "女"]

SPECS = {
    "village_move": {
        "table": "t_village_move",
        "new_fields": [
            ("household_no", "户号", "text", 0, 1, 1, None),
            ("householder", "户主姓名", "text", 0, 1, 1, None),
            ("gender", "性别", "select", 0, 1, 1, GENDER),
            ("age", "年龄", "number", 0, 1, 1, None),
            ("old_address", "原居住地址", "text", 0, 1, 1, None),
            ("new_address", "现居住地址", "text", 0, 1, 1, None),
            ("create_time", "创建时间", "text", 0, 1, 0, None),
        ],
        "rename": {"id_card": "身份证号码", "phone": "联系方式", "apply_date": "申请时间"},
        "hide": ["settle_date", "address"],
        "order": ["village_group", "household_no", "householder", "name", "gender", "id_card",
                  "age", "phone", "old_address", "new_address", "move_type", "apply_date",
                  "approve_status", "remark", "create_time"],
    },
    "rescue": {
        "table": "t_rescue",
        "new_fields": [
            ("householder", "户主姓名", "text", 0, 1, 1, None),
            ("approve_date", "审批日期", "date", 0, 1, 1, None),
            ("bank_name", "开户行", "text", 0, 1, 1, None),
            ("card_no", "社保卡号", "text", 0, 1, 1, None),
            ("pay_method", "发放方式", "select", 0, 1, 1, ["银行转账", "现金", "一卡通", "其他"]),
            ("pay_date", "发放日期", "date", 0, 1, 1, None),
            ("operator", "经办人", "text", 0, 1, 1, None),
            ("disease_name", "疾病名称", "text", 0, 1, 1, None),
            ("disaster_type", "灾害类型", "text", 0, 1, 1, None),
            ("school_grade", "就读学校及年级", "text", 0, 1, 1, None),
            ("family_income", "家庭年人均收入（元）", "number", 0, 1, 1, None),
            ("review_opinion", "民主评议意见", "text", 0, 1, 1, None),
            ("revisit_record", "救助后回访记录", "text", 0, 1, 1, None),
            ("revisit_date", "回访日期", "date", 0, 1, 1, None),
            ("is_party", "是否党员", "select", 0, 1, 1, ["否", "是"]),
            ("create_time", "创建时间", "text", 0, 1, 0, None),
        ],
        "rename": {"reason": "申请事由", "rescue_date": "申请日期", "status": "审批状态",
                   "amount": "救助金额（元）", "id_card": "身份证号码"},
        "hide": [],
        "order": ["village_group", "householder", "name", "id_card", "phone", "rescue_type",
                  "reason", "rescue_date", "status", "approve_date", "amount", "bank_name",
                  "card_no", "pay_method", "pay_date", "operator", "disease_name", "disaster_type",
                  "school_grade", "family_income", "review_opinion", "revisit_record",
                  "revisit_date", "is_party", "remark", "create_time"],
    },
    "left_child": {
        "table": "t_left_child",
        "new_fields": [
            ("household_no", "户号", "text", 0, 1, 1, None),
            ("id_card", "身份证号码", "text", 0, 1, 1, None),
            ("age", "年龄", "number", 0, 1, 1, None),
            ("grade", "年级", "text", 0, 1, 1, None),
            ("guardian_relation", "监护关系", "text", 0, 1, 1, None),
            ("parent_name", "外出务工家长", "text", 0, 1, 1, None),
            ("parent_phone", "家长电话", "text", 0, 1, 1, None),
            ("work_address", "务工地址", "text", 0, 1, 1, None),
            ("left_type", "留守类型", "select", 0, 1, 1, ["父母双方外出", "父母一方外出", "单亲留守", "其他"]),
            ("care_level", "关爱级别", "select", 0, 1, 1, ["高", "中", "低"]),
            ("visit_record", "走访记录", "text", 0, 1, 1, None),
            ("create_time", "创建时间", "text", 0, 1, 0, None),
        ],
        "rename": {"last_visit_date": "最近走访"},
        "hide": ["visit_status"],
        "order": ["village_group", "household_no", "name", "gender", "id_card", "birth_date",
                  "age", "school", "grade", "guardian_name", "guardian_relation", "guardian_phone",
                  "parent_name", "parent_phone", "work_address", "left_type", "care_level",
                  "last_visit_date", "visit_record", "remark", "create_time"],
    },
    "elderly": {
        "table": "t_elderly",
        "new_fields": [
            ("household_no", "户号", "text", 0, 1, 1, None),
            ("gender", "性别", "select", 0, 1, 1, GENDER),
            ("birth_date", "出生日期", "date", 0, 1, 1, None),
            ("living_situation", "居住情况", "select", 0, 1, 1, ["独居", "与配偶同住", "与子女同住", "养老机构", "其他"]),
            ("health_status", "健康状况", "select", 0, 1, 1, ["健康", "一般", "慢性病", "失能", "半失能"]),
            ("bank_name", "开户行", "text", 0, 1, 1, None),
            ("card_no", "社保卡号", "text", 0, 1, 1, None),
            ("living_subsidy", "生活补贴（元/月）", "number", 0, 1, 1, None),
            ("pension_type", "养老保险类型", "select", 0, 1, 1, ["城乡居民养老", "职工养老", "无"]),
            ("pension_amount", "养老金（元/月）", "number", 0, 1, 1, None),
            ("chronic_disease", "慢性疾病", "text", 0, 1, 1, None),
            ("emergency_contact", "紧急联系人", "text", 0, 1, 1, None),
            ("emergency_phone", "紧急联系电话", "text", 0, 1, 1, None),
            ("helper", "帮扶责任人", "text", 0, 1, 1, None),
            ("helper_phone", "帮扶人电话", "text", 0, 1, 1, None),
            ("last_visit", "最近走访", "date", 0, 1, 1, None),
            ("create_time", "创建时间", "text", 0, 1, 0, None),
        ],
        "rename": {"id_card": "身份证号码", "phone": "联系电话", "care_type": "养老方式"},
        "hide": ["subsidy_status", "expire_date"],
        "order": ["village_group", "household_no", "name", "gender", "id_card", "birth_date",
                  "age", "phone", "living_situation", "health_status", "care_type", "bank_name",
                  "card_no", "living_subsidy", "pension_type", "pension_amount", "chronic_disease",
                  "emergency_contact", "emergency_phone", "helper", "helper_phone", "last_visit",
                  "remark", "create_time"],
    },
    "veteran": {
        "table": "t_veteran",
        "new_fields": [
            ("household_no", "户号", "text", 0, 1, 1, None),
            ("householder", "户主姓名", "text", 0, 1, 1, None),
            ("gender", "性别", "select", 0, 1, 1, GENDER),
            ("age", "年龄", "number", 0, 1, 1, None),
            ("military_years", "军龄(年)", "number", 0, 1, 1, None),
            ("service_type", "军种", "select", 0, 1, 1, ["陆军", "海军", "空军", "火箭军", "武警", "其他"]),
            ("political_status", "政治面貌", "select", 0, 1, 1, ["中共党员", "共青团员", "群众", "其他"]),
            ("honor_awards", "立功受奖情况", "text", 0, 1, 1, None),
            ("pension_type", "优抚类别", "select", 0, 1, 1, ["烈士遗属", "因公牺牲军人遗属", "病故军人遗属", "在乡老复员军人", "带病回乡退伍军人", "参战退役人员", "其他"]),
            ("work_address", "务工地址", "text", 0, 1, 1, None),
            ("current_address", "现居住地址", "text", 0, 1, 1, None),
            ("unit_number", "服役部队番号", "text", 0, 1, 1, None),
            ("discharge_no", "退役证编号", "text", 0, 1, 1, None),
            ("employment_status", "就业安置情况", "text", 0, 1, 1, None),
            ("entrepreneurship", "创业情况", "text", 0, 1, 1, None),
            ("support_record", "困难帮扶记录", "text", 0, 1, 1, None),
            ("visit_record", "八一/春节走访记录", "text", 0, 1, 1, None),
            ("annual_check_status", "年审状态", "select", 0, 1, 1, ["已年审", "未年审"]),
            ("check_date", "审核日期", "date", 0, 1, 1, None),
        ],
        "rename": {"military_type": "人员类别", "enroll_date": "入伍时间", "discharge_date": "退伍时间",
                   "subsidy_status": "优抚对象", "phone": "联系方式", "id_card": "身份证号码"},
        "hide": [],
        "order": ["village_group", "household_no", "householder", "name", "gender", "id_card",
                  "age", "military_type", "enroll_date", "discharge_date", "military_years",
                  "service_type", "political_status", "honor_awards", "subsidy_status",
                  "pension_type", "phone", "work_address", "current_address", "unit_number",
                  "discharge_no", "employment_status", "entrepreneurship", "support_record",
                  "visit_record", "annual_check_status", "check_date", "remark"],
    },
    "oversea": {
        "table": "t_oversea",
        "new_fields": [
            ("household_no", "户号", "text", 0, 1, 1, None),
            ("householder", "户主姓名", "text", 0, 1, 1, None),
            ("gender", "性别", "select", 0, 1, 1, GENDER),
            ("age", "年龄", "number", 0, 1, 1, None),
            ("country", "出境国家/地区", "text", 0, 1, 1, None),
            ("abroad_reason", "出境事由", "select", 0, 1, 1, ["务工", "留学", "经商", "探亲", "移民", "其他"]),
            ("expected_return_date", "预计归国日期", "date", 0, 1, 1, None),
            ("remaining_days", "剩余天数", "number", 0, 1, 1, None),
            ("visa_type", "签证类型", "text", 0, 1, 1, None),
            ("household_address", "户籍地址", "text", 0, 1, 1, None),
            ("emergency_contact", "紧急联系人", "text", 0, 1, 1, None),
            ("emergency_phone", "紧急联系电话", "text", 0, 1, 1, None),
            ("abroad_contact", "国外联系方式", "text", 0, 1, 1, None),
            ("regular_contact", "是否定期联系", "select", 0, 1, 1, ["是", "否"]),
            ("contact_relation", "联系人关系", "text", 0, 1, 1, None),
            ("abroad_unit", "境外工作单位/学校", "text", 0, 1, 1, None),
            ("return_destination", "归国后去向", "text", 0, 1, 1, None),
        ],
        "rename": {"visa_no": "护照号码", "visa_expire_date": "签证有效期", "return_date": "实际归国日期",
                   "status": "归国状态", "phone": "联系电话", "id_card": "身份证号码"},
        "hide": [],
        "order": ["village_group", "household_no", "householder", "name", "gender", "id_card",
                  "age", "phone", "country", "abroad_reason", "go_abroad_date",
                  "expected_return_date", "remaining_days", "status", "visa_no", "visa_type",
                  "visa_expire_date", "household_address", "emergency_contact", "emergency_phone",
                  "abroad_contact", "regular_contact", "contact_relation", "abroad_unit",
                  "return_date", "return_destination", "remark"],
    },
    "three_capital": {
        "table": "t_three_capital",
        "new_fields": [
            ("location", "坐落位置", "text", 0, 1, 1, None),
            ("quantity", "数量", "number", 0, 1, 1, None),
            ("caretaker", "管护人", "text", 0, 1, 1, None),
            ("create_time", "创建时间", "text", 0, 1, 0, None),
        ],
        "rename": {"amount": "原值(元)", "status": "使用状态", "asset_name": "资产名称"},
        "hide": ["owner", "manage_date", "village_group"],
        "order": ["asset_name", "asset_type", "location", "quantity", "amount", "status",
                  "caretaker", "remark", "create_time"],
    },
    "homestead": {
        "table": "t_homestead",
        "new_fields": [
            ("floor_count", "房屋层数", "number", 0, 1, 1, None),
            ("finish_date", "竣工时间", "date", 0, 1, 1, None),
            ("illegal_build", "违建", "select", 0, 1, 1, ["否", "是"]),
            ("create_time", "创建时间", "text", 0, 1, 0, None),
        ],
        "rename": {"householder": "户主", "build_area": "确权面积(㎡)", "apply_date": "建房申请时间"},
        "hide": ["id_card", "land_no", "start_date"],
        "order": ["householder", "village_group", "build_area", "apply_date", "approve_status",
                  "floor_count", "finish_date", "illegal_build", "remark", "create_time"],
    },
    "drowning_prevent": {
        "table": "t_drowning_prevent",
        "new_fields": [
            ("location", "点位位置", "text", 0, 1, 1, None),
            ("patrol_person", "巡河人员", "text", 0, 1, 1, None),
            ("patrol_time", "巡河时间", "date", 0, 1, 1, None),
            ("hazard", "安全隐患", "text", 0, 1, 1, None),
            ("rectification_status", "整改状态", "select", 0, 1, 1, ["未整改", "整改中", "已整改"]),
            ("warning_facility", "警示设施", "select", 0, 1, 1, ["警示牌", "围栏", "救生圈", "警示牌+围栏", "无"]),
            ("create_time", "创建时间", "text", 0, 1, 0, None),
        ],
        "rename": {"water_area": "水域名称"},
        "hide": ["area_type", "danger_level", "responsible", "responsible_phone", "sign_count",
                 "check_date", "village_group"],
        "order": ["water_area", "location", "patrol_person", "patrol_time", "hazard",
                  "rectification_status", "warning_facility", "remark", "create_time"],
    },
    "village_public": {
        "table": "t_village_public",
        "new_fields": [
            ("location", "公示地点", "text", 0, 1, 1, None),
            ("create_time", "创建时间", "text", 0, 1, 0, None),
        ],
        "rename": {"public_title": "公开事项", "publish_date": "公示开始", "expire_date": "公示结束",
                   "status": "到期状态"},
        "hide": ["public_type", "public_content", "village_group"],
        "order": ["public_title", "publish_date", "expire_date", "location", "status", "remark",
                  "create_time"],
    },
    "public_job": {
        "table": "t_public_job",
        "new_fields": [
            ("phone", "联系电话", "text", 0, 1, 1, None),
            ("area", "责任片区", "text", 0, 1, 1, None),
            ("salary", "工资（元/年）", "number", 0, 1, 1, None),
            ("bank_name", "开户行", "text", 0, 1, 1, None),
            ("card_no", "社保卡号", "text", 0, 1, 1, None),
            ("create_time", "创建时间", "text", 0, 1, 0, None),
        ],
        "rename": {"person_name": "姓名", "id_card": "身份证号码", "job_name": "岗位名称"},
        "hide": ["job_type", "contract_start", "contract_end", "status", "village_group"],
        "order": ["person_name", "id_card", "phone", "job_name", "area", "salary", "bank_name",
                  "card_no", "remark", "create_time"],
    },
    "rural_industry": {
        "table": "t_rural_industry",
        "new_fields": [
            ("location", "地块位置", "text", 0, 1, 1, None),
            ("production_date", "投产时间", "date", 0, 1, 1, None),
            ("employment_count", "带动就业人数", "number", 0, 1, 1, None),
            ("create_time", "创建时间", "text", 0, 1, 0, None),
        ],
        "rename": {"industry_type": "产业类型", "owner": "负责人", "amount": "年度收益(元)"},
        "hide": ["project_name", "scale", "manage_date", "status", "village_group"],
        "order": ["industry_type", "location", "production_date", "owner", "amount",
                  "employment_count", "remark", "create_time"],
    },
    "project": {
        "table": "t_project",
        "new_fields": [
            ("paid_amount", "已支付(元)", "number", 0, 1, 1, None),
            ("acceptance_status", "验收状态", "select", 0, 1, 1, ["未验收", "已验收", "验收不通过"]),
            ("create_time", "创建时间", "text", 0, 1, 0, None),
        ],
        "rename": {"contract_start": "开工时间", "contract_end": "竣工时间", "budget": "总预算(元)",
                   "project_name": "项目名称", "contractor": "施工单位", "progress": "工程进度(%)"},
        "hide": ["project_type", "payment_node", "village_group"],
        "change_type": {"progress": ("number", 0)},
        "order": ["project_name", "contract_start", "contract_end", "contractor", "budget",
                  "paid_amount", "progress", "acceptance_status", "remark", "create_time"],
    },
    "visit_record": {
        "table": "t_visit_record",
        "new_fields": [
            ("rectification", "整改措施", "text", 0, 1, 1, None),
            ("revisit_situation", "回访情况", "text", 0, 1, 1, None),
            ("create_time", "创建时间", "text", 0, 1, 0, None),
        ],
        "rename": {"visit_person": "走访人员", "visit_target": "走访对象", "visit_date": "走访时间",
                   "content": "群众诉求", "result": "办结状态", "remark": "备注"},
        "hide": ["visit_type", "helper", "village_group"],
        "order": ["visit_target", "visit_date", "visit_person", "content", "rectification",
                  "result", "revisit_situation", "remark", "create_time"],
    },
}

# 移风易俗：红事/白事两个新台账
CUSTOM_MENUS = [
    {
        "code": "custom_red", "name": "移风易俗-红事统计表", "table": "t_custom_red",
        "fields": [
            ("village_group", "村名", "text", 0, 1, 1, None),
            ("householder", "户主", "text", 0, 1, 1, None),
            ("event_type", "红事类别", "select", 0, 1, 1, ["婚嫁", "乔迁", "满月", "寿宴", "升学", "其他"]),
            ("event_date", "办事时间", "date", 0, 1, 1, None),
            ("banquet_standard", "宴席标准(桌/价格)", "text", 0, 1, 1, None),
            ("wine_standard", "烟酒标准(价格)", "text", 0, 1, 1, None),
            ("consultant", "看日子先生及电话号码", "text", 0, 1, 1, None),
        ],
    },
    {
        "code": "custom_white", "name": "移风易俗-白事统计表", "table": "t_custom_white",
        "fields": [
            ("village_group", "村名", "text", 0, 1, 1, None),
            ("householder", "户主", "text", 0, 1, 1, None),
            ("deceased_name", "去世人员", "text", 0, 1, 1, None),
            ("deceased_time", "去世时间", "date", 0, 1, 1, None),
            ("funeral_time", "出殡时间", "date", 0, 1, 1, None),
            ("banquet_standard", "宴席标准(桌/价格)", "text", 0, 1, 1, None),
            ("wine_standard", "烟酒标准(价格)", "text", 0, 1, 1, None),
            ("consultant", "看日子先生及电话号码", "text", 0, 1, 1, None),
        ],
    },
]


def upsert_field(cur, menu, table, pf, label, ftype, req, lst, form, opts):
    ensure_column(cur, table, pf, SQLITE_TYPE_MAP[ftype])
    row = cur.execute("SELECT id FROM sys_field_config WHERE menu_code=? AND physical_field=?", (menu, pf)).fetchone()
    if row:
        cur.execute(
            "UPDATE sys_field_config SET display_label=?,data_type=?,is_required=?,show_in_list=?,show_in_form=?,is_deleted=0,options_json=?,update_time=? WHERE id=?",
            (label, ftype, req, lst, form, dumps(opts) if opts else None, NOW, row["id"]))
    else:
        comp = "number" if ftype == "number" else ("select" if ftype == "select" else ("date" if ftype == "date" else ("datetime" if ftype == "datetime" else "input")))
        is_sys = 1 if pf == "create_time" else 0
        cur.execute(
            "INSERT INTO sys_field_config(menu_code,physical_field,display_label,data_type,form_component,is_system,show_in_list,show_in_form,is_required,sort_order,is_deleted,options_json,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (menu, pf, label, ftype, comp, is_sys, lst, form, req, 0, 0, dumps(opts) if opts else None, NOW, NOW))


def migrate_menu(cur, menu, spec):
    table = spec["table"]
    for pf, label, ftype, req, lst, form, opts in spec["new_fields"]:
        upsert_field(cur, menu, table, pf, label, ftype, req, lst, form, opts)
    for pf, label in spec.get("rename", {}).items():
        cur.execute("UPDATE sys_field_config SET display_label=?,update_time=? WHERE menu_code=? AND physical_field=?",
                    (label, NOW, menu, pf))
    for pf in spec.get("hide", []):
        cur.execute("UPDATE sys_field_config SET show_in_list=0,show_in_form=0,update_time=? WHERE menu_code=? AND physical_field=?",
                    (NOW, menu, pf))
    for pf, (ftype, default) in spec.get("change_type", {}).items():
        cur.execute("UPDATE sys_field_config SET data_type=?,form_component=?,options_json=NULL,update_time=? WHERE menu_code=? AND physical_field=?",
                    (ftype, "number" if ftype == "number" else "input", NOW, menu, pf))
        if ftype == "number":
            cur.execute(f"UPDATE {table} SET {pf}=? WHERE {pf} NOT IN (SELECT {pf} FROM {table} WHERE typeof({pf}) IN ('integer','real'))",
                        (default,))
    cur.execute("UPDATE sys_field_config SET show_in_list=1,display_label='备注',update_time=? WHERE menu_code=? AND physical_field=?",
                (NOW, menu, "remark"))
    order = spec["order"]
    all_rows = cur.execute("SELECT id,physical_field FROM sys_field_config WHERE menu_code=? AND is_deleted=0", (menu,)).fetchall()
    id_by_field = {r["physical_field"]: r["id"] for r in all_rows}
    tail = 90
    for pf, fid in id_by_field.items():
        if pf in order:
            cur.execute("UPDATE sys_field_config SET sort_order=?,update_time=? WHERE id=?",
                        (order.index(pf) + 1, NOW, fid))
        else:
            cur.execute("UPDATE sys_field_config SET sort_order=?,update_time=? WHERE id=?", (tail, NOW, fid))
            tail += 1


def ensure_custom_menu(cur, spec):
    code, table, name = spec["code"], spec["table"], spec["name"]
    cur.execute(f"""CREATE TABLE IF NOT EXISTS {table} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        create_time TEXT, update_time TEXT
    )""")
    for pf, label, ftype, req, lst, form, opts in spec["fields"]:
        ensure_column(cur, table, pf, SQLITE_TYPE_MAP[ftype])
        upsert_field(cur, code, table, pf, label, ftype, req, lst, form, opts)
    upsert_field(cur, code, table, "create_time", "创建时间", "text", 0, 0, 0, None)
    row = cur.execute("SELECT id FROM sys_menu_config WHERE code=?", (code,)).fetchone()
    if not row:
        cur.execute(
            "INSERT INTO sys_menu_config(code,name,parent_code,sort_order,is_visible,is_ledger,table_name,path,create_time) VALUES(?,?,?,?,?,?,?,?,?)",
            (code, name, "gov", 50, 1, 1, table, None, NOW))


def main():
    conn = get_conn()
    cur = conn.cursor()
    for menu, spec in SPECS.items():
        migrate_menu(cur, menu, spec)
        cur.execute("INSERT INTO sys_oper_log(user_id,username,action,module,detail,ip,create_time) VALUES(?,?,?,?,?,?,?)",
                    (1, "admin", "台账字段规格调整", "字段配置", f"{menu}台账按需求规格补齐字段", "127.0.0.1", NOW))
    # 移风易俗红事/白事
    for spec in CUSTOM_MENUS:
        ensure_custom_menu(cur, spec)
        cur.execute("INSERT INTO sys_oper_log(user_id,username,action,module,detail,ip,create_time) VALUES(?,?,?,?,?,?,?)",
                    (1, "admin", "台账字段规格调整", "字段配置", f"新增{spec['name']}", "127.0.0.1", NOW))
    # 原移风易俗台账菜单隐藏（数据保留）
    cur.execute("UPDATE sys_menu_config SET is_visible=0 WHERE code='custom_rural'")
    conn.commit()
    conn.close()
    print("迁移完成：15 个台账字段按需求规格补齐，新增移风易俗红事/白事台账")


if __name__ == "__main__":
    main()
