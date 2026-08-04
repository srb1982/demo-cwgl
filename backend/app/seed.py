"""数据库初始化与种子数据：系统表 + 元数据表 + 22套业务台账表 + 菜单 + 预置字段库 + 管理员"""
import hashlib
import os
from datetime import datetime

from . import config
from .database import get_conn, dumps, SQLITE_TYPE_MAP


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()


# ---------------------------------------------------------------
# 台账表定义
# ---------------------------------------------------------------
def F(field, label, ftype="text", required=False, show_list=True, show_form=True, options=None):
    return {
        "field": field,
        "label": label,
        "type": ftype,
        "required": required,
        "show_list": show_list,
        "show_form": show_form,
        "options": options,
    }


COMMON = [
    F("village_group", "村民组", "text", False, True, True),
    F("remark", "备注", "text", False, False, True),
]

LEDGERS = [
    {
        "code": "villager", "name": "村民信息台账", "table": "t_villager_info", "group": "base",
        "fields": [
            F("village_group", "村民组", "text", False, True, True),
            F("household_no", "户号", "text", False, True, True),
            F("population", "人口数", "number", False, True, True),
            F("householder", "户主姓名", "text", False, True, True),
            F("name", "姓名", "text", True, True, True),
            F("relation", "与户主关系", "select", False, True, True, ["本人", "配偶", "子女", "父母", "祖孙", "其他"]),
            F("gender", "性别", "select", True, True, True, ["男", "女"]),
            F("id_card", "身份证号码", "text", True, True, True),
            F("age", "年龄", "number", False, True, True),
            F("phone", "联系方式", "text", False, True, True),
            F("address", "现居住地址", "text", False, True, True),
            F("work_type", "务工类型", "select", False, True, True, ["在家务农", "本地务工", "县外务工", "自主创业", "无"]),
            F("work_address", "务工地址", "text", False, True, True),
            F("key_mark", "重点标识", "select", False, True, True, ["无", "低保", "残疾", "五保", "建档立卡", "优抚对象", "其他"]),
            F("education", "文化程度", "select", False, True, True, ["文盲", "小学", "初中", "高中", "中专", "大专", "本科及以上"]),
            F("ethnic", "民族", "select", False, True, True, ["汉族", "壮族", "回族", "满族", "苗族", "维吾尔族", "彝族", "土家族", "蒙古族", "其他"]),
            F("status", "状态", "select", False, True, True, ["正常", "外出", "迁出", "死亡", "已注销"]),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "party_member", "name": "党员信息台账", "table": "t_party_member", "group": "base",
        "fields": [
            F("village_group", "村民组", "text", False, True, True),
            F("household_no", "户号", "text", False, True, True),
            F("householder", "户主姓名", "text", False, True, True),
            F("name", "姓名", "text", True, True, True),
            F("gender", "性别", "select", True, True, True, ["男", "女"]),
            F("id_card", "身份证号码", "text", True, True, True),
            F("age", "年龄", "number", False, True, True),
            F("join_date", "入党时间", "date", True, True, True),
            F("positive_date", "转正时间", "date", False, True, True),
            F("party_age", "党龄", "number", False, True, True),
            F("phone", "联系方式", "text", False, True, True),
            F("work_address", "务工地址", "text", False, True, True),
            F("fee_amount", "党费（元/年）", "number", False, True, True),
            F("remark", "备注", "text", False, True, True),
            F("fee_status", "党费收缴", "select", False, False, True, ["正常", "欠缴", "免缴"]),
            F("party_branch", "所在支部", "text", False, False, False),
        ],
    },
    {
        "code": "disabled", "name": "残疾人信息台账", "table": "t_disabled", "group": "base",
        "fields": [
            F("village_group", "村民组", "text", False, True, True),
            F("household_no", "户号", "text", False, True, True),
            F("householder", "户主姓名", "text", False, True, True),
            F("name", "姓名", "text", True, True, True),
            F("gender", "性别", "select", True, True, True, ["男", "女"]),
            F("id_card", "身份证号码", "text", True, True, True),
            F("age", "年龄", "number", False, True, True),
            F("disability_type", "残疾类型", "select", True, True, True, ["视力", "听力", "言语", "肢体", "智力", "精神", "多重"]),
            F("disability_level", "残疾等级", "select", True, True, True, ["一级", "二级", "三级", "四级"]),
            F("disability_photo", "残疾证照片", "image", False, True, True),
            F("phone", "联系方式", "text", False, True, True),
            F("low_income", "是否低保", "select", False, True, True, ["是", "否"]),
            F("certificate_date", "办证日期", "date", False, True, True),
            F("renew_date", "换证日期", "date", False, True, True),
            F("guardian", "监护人", "text", False, True, True),
            F("guardian_phone", "监护人电话", "text", False, True, True),
            F("remark", "备注", "text", False, True, True),
            F("certificate_no", "残疾证号", "text", False, False, False),
            F("expire_date", "证件到期日", "date", False, False, True),
            F("cert_status", "证件状态", "select", False, False, True, ["正常", "即将到期", "已到期", "换证中"]),
        ],
    },
    {
        "code": "low_income", "name": "低保信息台账", "table": "t_low_income", "group": "base",
        "fields": [
            F("village_group", "村民组", "text", False, True, True),
            F("household_no", "户号", "text", False, True, True),
            F("householder", "户主姓名", "text", False, True, True),
            F("name", "姓名", "text", True, True, True),
            F("gender", "性别", "select", False, True, True, ["男", "女"]),
            F("id_card", "身份证号码", "text", True, True, True),
            F("age", "年龄", "number", False, True, True),
            F("is_disabled", "是否残疾", "select", False, True, True, ["是", "否"]),
            F("disability_type", "残疾类型", "select", False, True, True, ["视力", "听力", "言语", "肢体", "智力", "精神", "多重"]),
            F("disability_level", "残疾等级", "select", False, True, True, ["一级", "二级", "三级", "四级"]),
            F("low_income_type", "低保类型", "select", False, True, True, ["城市低保", "农村低保"]),
            F("phone", "联系方式", "text", False, True, True),
            F("start_date", "开始时间", "date", False, True, True),
            F("monthly_amount", "保障标准（元/月）", "number", True, True, True),
            F("relief_type", "救助类型", "select", False, True, True, ["临时救助", "医疗救助", "教育救助", "住房救助", "就业救助", "其他"]),
            F("bank", "开户行", "text", False, True, True),
            F("social_card", "社保卡号", "text", False, True, True),
            F("adjust_record", "动态调整记录", "text", False, True, True),
            F("remark", "备注", "text", False, True, True),
            F("end_date", "享受结束日期", "date", False, False, True),
            F("status", "保障状态", "select", False, False, True, ["在保", "退出", "已停发"]),
        ],
    },
    {
        "code": "fee_collect", "name": "三费收缴台账", "table": "t_fee_collect", "group": "base",
        "fields": [
            F("village_group", "村民组", "text", False, True, True),
            F("household_no", "户号", "text", False, True, True),
            F("family_count", "人口数", "number", False, True, True),
            F("householder", "户主姓名", "text", False, True, True),
            F("name", "姓名", "text", True, True, True),
            F("relation", "与户主关系", "select", False, True, True, ["本人", "配偶", "子女", "父母", "祖孙", "其他"]),
            F("id_card", "身份证号码", "text", True, True, True),
            F("age", "年龄", "number", False, True, True),
            F("identity_mark", "身份标记", "select", False, True, True, ["党员", "团员", "群众", "低保", "五保", "优抚对象", "村干部", "其他"]),
            F("medical_status", "医疗保险", "select", True, True, True, ["已缴", "未缴", "减免"]),
            F("pension_status", "养老保险", "select", True, True, True, ["已缴", "未缴", "减免"]),
            F("supplement_status", "大病补充", "select", True, True, True, ["已缴", "未缴", "减免"]),
            F("amount", "家庭金额", "number", False, True, True),
            F("phone", "联系方式", "text", False, True, True),
            F("pay_method", "缴费方式", "select", False, True, True, ["微信", "支付宝", "现金", "银行代扣", "村集体代缴", "其他"]),
            F("pay_time", "缴费时间", "date", False, True, True),
            F("operator", "操作人", "text", False, True, True),
            F("fee_year", "缴费年度", "text", True, True, True),
            F("attachment", "附件", "image", False, True, True),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "reservoir_migrant", "name": "水库移民台账", "table": "t_reservoir_migrant", "group": "base",
        "fields": [
            F("name", "姓名", "text", True, True, True),
            F("id_card", "身份证号", "text", True, True, True),
            F("phone", "联系电话", "text", False, True, True),
            F("migrant_no", "移民编号", "text", False, True, True),
            F("subsidy_amount", "补助金额", "number", False, True, True),
            F("migrate_date", "迁移时间", "date", False, True, True),
            F("address", "安置地址", "text", False, True, True),
        ] + COMMON,
    },
    {
        "code": "village_move", "name": "一般搬迁台账", "table": "t_village_move", "group": "base",
        "fields": [
            F("name", "姓名", "text", True, True, True),
            F("id_card", "身份证号", "text", True, True, True),
            F("phone", "联系电话", "text", False, True, True),
            F("move_type", "搬迁类型", "select", True, True, True, ["易地搬迁", "生态搬迁", "工程搬迁", "其他"]),
            F("apply_date", "申请日期", "date", False, True, True),
            F("approve_status", "审批状态", "select", False, True, True, ["待审批", "已审批", "已入住", "超时未办"]),
            F("settle_date", "安置入住日期", "date", False, True, True),
            F("address", "安置地址", "text", False, True, True),
        ] + COMMON,
    },
    {
        "code": "rescue", "name": "困难群众救助台账", "table": "t_rescue", "group": "civil",
        "fields": [
            F("name", "姓名", "text", True, True, True),
            F("id_card", "身份证号", "text", True, True, True),
            F("phone", "联系电话", "text", False, True, True),
            F("rescue_type", "救助类型", "select", True, True, True, ["临时救助", "医疗救助", "教育救助", "住房救助", "其他"]),
            F("reason", "救助原因", "text", False, True, True),
            F("amount", "救助金额", "number", False, True, True),
            F("rescue_date", "救助日期", "date", False, True, True),
            F("status", "救助状态", "select", False, True, True, ["申请中", "已救助", "已结束"]),
        ] + COMMON,
    },
    {
        "code": "left_child", "name": "留守儿童台账", "table": "t_left_child", "group": "civil",
        "fields": [
            F("name", "姓名", "text", True, True, True),
            F("gender", "性别", "select", True, True, True, ["男", "女"]),
            F("birth_date", "出生日期", "date", False, True, True),
            F("guardian_name", "监护人姓名", "text", True, True, True),
            F("guardian_phone", "监护人电话", "text", True, True, True),
            F("school", "就读学校", "text", False, True, True),
            F("last_visit_date", "最近走访日期", "date", False, True, True),
            F("visit_status", "走访状态", "select", False, True, True, ["正常", "超期未走访"]),
        ] + COMMON,
    },
    {
        "code": "elderly", "name": "老年人管理台账", "table": "t_elderly", "group": "civil",
        "fields": [
            F("name", "姓名", "text", True, True, True),
            F("id_card", "身份证号", "text", True, True, True),
            F("phone", "联系电话", "text", False, True, True),
            F("age", "年龄", "number", False, True, True),
            F("subsidy_status", "补贴状态", "select", False, True, True, ["正常", "待续办", "已停发"]),
            F("expire_date", "补贴到期日", "date", False, True, True),
            F("care_type", "养老方式", "select", False, True, True, ["居家养老", "集中供养", "日间照料"]),
        ] + COMMON,
    },
    {
        "code": "veteran", "name": "现役退役军人台账", "table": "t_veteran", "group": "civil",
        "fields": [
            F("name", "姓名", "text", True, True, True),
            F("id_card", "身份证号", "text", True, True, True),
            F("phone", "联系电话", "text", False, True, True),
            F("military_type", "服役类型", "select", True, True, True, ["义务兵", "士官", "军官", "志愿兵"]),
            F("enroll_date", "入伍日期", "date", False, True, True),
            F("discharge_date", "退伍日期", "date", False, True, True),
            F("subsidy_status", "优抚状态", "select", False, True, True, ["正常", "待续办", "已停发"]),
        ] + COMMON,
    },
    {
        "code": "oversea", "name": "境外人员台账", "table": "t_oversea", "group": "civil",
        "fields": [
            F("name", "姓名", "text", True, True, True),
            F("id_card", "身份证号", "text", True, True, True),
            F("phone", "联系电话", "text", False, True, True),
            F("visa_no", "签证号", "text", False, True, True),
            F("visa_expire_date", "签证到期日", "date", False, True, True),
            F("go_abroad_date", "出境日期", "date", False, True, True),
            F("return_date", "回国日期", "date", False, True, True),
            F("status", "状态", "select", False, True, True, ["境外", "已回国", "待归国"]),
        ] + COMMON,
    },
    {
        "code": "three_capital", "name": "三资管理台账", "table": "t_three_capital", "group": "gov",
        "fields": [
            F("asset_name", "资产名称", "text", True, True, True),
            F("asset_type", "资产类型", "select", True, True, True, ["资金", "资产", "资源"]),
            F("amount", "金额/估值", "number", False, True, True),
            F("owner", "归属主体", "text", False, True, True),
            F("manage_date", "登记日期", "date", False, True, True),
            F("status", "状态", "select", False, True, True, ["正常", "处置中", "已出租"]),
        ] + COMMON,
    },
    {
        "code": "homestead", "name": "宅基地建房台账", "table": "t_homestead", "group": "gov",
        "fields": [
            F("householder", "户主姓名", "text", True, True, True),
            F("id_card", "身份证号", "text", True, True, True),
            F("land_no", "宅基地证号", "text", False, True, True),
            F("build_area", "建房面积", "number", False, True, True),
            F("apply_date", "申请日期", "date", False, True, True),
            F("approve_status", "审批状态", "select", False, True, True, ["待审批", "已批准", "建设中", "已完工"]),
            F("start_date", "开工日期", "date", False, True, True),
        ] + COMMON,
    },
    {
        "code": "drowning_prevent", "name": "防溺水综治台账", "table": "t_drowning_prevent", "group": "gov",
        "fields": [
            F("water_area", "水域名称", "text", True, True, True),
            F("area_type", "水域类型", "select", True, True, True, ["河流", "水库", "池塘", "沟渠"]),
            F("danger_level", "风险等级", "select", True, True, True, ["高", "中", "低"]),
            F("responsible", "责任人", "text", True, True, True),
            F("responsible_phone", "责任人电话", "text", False, True, True),
            F("sign_count", "警示牌数量", "number", False, True, True),
            F("check_date", "最近巡查日期", "date", False, True, True),
        ] + COMMON,
    },
    {
        "code": "petition", "name": "信访矛盾纠纷台账", "table": "t_petition", "group": "gov",
        "fields": [
            F("petitioner", "反映人", "text", True, True, True),
            F("phone", "联系电话", "text", False, True, True),
            F("issue_type", "问题类型", "select", True, True, True, ["土地纠纷", "邻里纠纷", "民生诉求", "其他"]),
            F("content", "诉求内容", "text", True, True, True),
            F("handle_person", "处理人", "text", False, True, True),
            F("handle_status", "处理状态", "select", False, True, True, ["待处理", "处理中", "已办结"]),
            F("handle_date", "办结日期", "date", False, True, True),
        ] + COMMON,
    },
    {
        "code": "village_public", "name": "村务公开台账", "table": "t_village_public", "group": "gov",
        "fields": [
            F("public_title", "公开标题", "text", True, True, True),
            F("public_type", "公开类型", "select", True, True, True, ["财务公开", "党务公开", "村务公开", "其他"]),
            F("public_content", "公开内容", "text", True, True, True),
            F("publish_date", "公开日期", "date", True, True, True),
            F("expire_date", "公示到期日", "date", False, True, True),
            F("status", "状态", "select", False, True, True, ["公示中", "已到期"]),
        ] + COMMON,
    },
    {
        "code": "public_job", "name": "公益性岗位台账", "table": "t_public_job", "group": "gov",
        "fields": [
            F("job_name", "岗位名称", "text", True, True, True),
            F("person_name", "在岗人员", "text", True, True, True),
            F("id_card", "身份证号", "text", False, True, True),
            F("job_type", "岗位类型", "select", True, True, True, ["保洁", "护林", "巡逻", "看护", "其他"]),
            F("contract_start", "合同开始", "date", False, True, True),
            F("contract_end", "合同到期", "date", False, True, True),
            F("status", "在岗状态", "select", False, True, True, ["在岗", "已离职"]),
        ] + COMMON,
    },
    {
        "code": "custom_rural", "name": "移风易俗台账", "table": "t_custom_rural", "group": "gov",
        "fields": [
            F("event_name", "事项名称", "text", True, True, True),
            F("event_type", "事项类型", "select", True, True, True, ["红事", "白事", "其他"]),
            F("household", "事主家庭", "text", False, True, True),
            F("event_date", "发生日期", "date", False, True, True),
            F("custom_type", "新风类型", "select", False, True, True, ["简办", "新办", "示范引领"]),
        ] + COMMON,
    },
    {
        "code": "rural_industry", "name": "乡村产业台账", "table": "t_rural_industry", "group": "gov",
        "fields": [
            F("project_name", "产业项目", "text", True, True, True),
            F("industry_type", "产业类型", "select", True, True, True, ["种植", "养殖", "加工", "乡村旅游", "电商"]),
            F("scale", "经营规模", "text", False, True, True),
            F("amount", "投入金额", "number", False, True, True),
            F("owner", "经营主体", "text", False, True, True),
            F("manage_date", "登记日期", "date", False, True, True),
            F("status", "经营状态", "select", False, True, True, ["运营中", "建设中", "已停办"]),
        ] + COMMON,
    },
    {
        "code": "project", "name": "工程项目台账", "table": "t_project", "group": "gov",
        "fields": [
            F("project_name", "项目名称", "text", True, True, True),
            F("project_type", "项目类型", "select", True, True, True, ["基础设施", "公共服务", "产业项目", "其他"]),
            F("budget", "预算金额", "number", False, True, True),
            F("contractor", "施工单位", "text", False, True, True),
            F("contract_start", "合同开始", "date", False, True, True),
            F("contract_end", "合同结束", "date", False, True, True),
            F("payment_node", "款项支付节点", "text", False, True, True),
            F("progress", "项目进度", "select", False, True, True, ["筹备", "施工中", "验收中", "已完工"]),
        ] + COMMON,
    },
    {
        "code": "visit_record", "name": "走访帮扶台账", "table": "t_visit_record", "group": "gov",
        "fields": [
            F("visit_person", "走访人", "text", True, True, True),
            F("visit_target", "走访对象", "text", True, True, True),
            F("visit_type", "走访类型", "select", True, True, True, ["定期走访", "节日慰问", "结对帮扶", "回访"]),
            F("visit_date", "走访日期", "date", True, True, True),
            F("content", "走访内容", "text", False, True, True),
            F("helper", "帮扶人", "text", False, True, True),
            F("result", "办理结果", "text", False, True, True),
        ] + COMMON,
    },
]

MENUS = [
    {"code": "base", "name": "基础人口台账", "parent": None, "sort": 1, "is_ledger": 0, "table": None, "path": None},
    {"code": "civil", "name": "民政特殊人群", "parent": None, "sort": 2, "is_ledger": 0, "table": None, "path": None},
    {"code": "gov", "name": "村级治理业务", "parent": None, "sort": 3, "is_ledger": 0, "table": None, "path": None},
    {"code": "archive", "name": "文档归档中心", "parent": None, "sort": 4, "is_ledger": 0, "table": None, "path": "/archive"},
    {"code": "warning", "name": "智能预警中心", "parent": None, "sort": 5, "is_ledger": 0, "table": None, "path": "/warning"},
    {"code": "fee", "name": "三费收缴面板", "parent": None, "sort": 6, "is_ledger": 0, "table": None, "path": "/fee-panel"},
    {"code": "screen", "name": "村务数据大屏", "parent": None, "sort": 7, "is_ledger": 0, "table": None, "path": "/dashboard"},
    {"code": "system", "name": "系统管理", "parent": None, "sort": 8, "is_ledger": 0, "table": None, "path": None},
    {"code": "sys_user", "name": "用户账号管理", "parent": "system", "sort": 1, "is_ledger": 0, "table": None, "path": "/system/users"},
    {"code": "sys_menu", "name": "菜单配置", "parent": "system", "sort": 2, "is_ledger": 0, "table": None, "path": "/system/menus"},
    {"code": "sys_field", "name": "台账字段配置", "parent": "system", "sort": 3, "is_ledger": 0, "table": None, "path": "/system/fields"},
    {"code": "sys_log", "name": "操作日志", "parent": "system", "sort": 4, "is_ledger": 0, "table": None, "path": "/system/logs"},
    {"code": "sys_backup", "name": "数据备份恢复", "parent": "system", "sort": 5, "is_ledger": 0, "table": None, "path": "/system/backup"},
    {"code": "sys_config", "name": "系统参数配置", "parent": "system", "sort": 6, "is_ledger": 0, "table": None, "path": "/system/config"},
]

FIELD_LIBRARY = [
    {"name": "name", "label": "姓名", "data_type": "text", "form_component": "input", "options": None},
    {"name": "id_card", "label": "身份证号", "data_type": "text", "form_component": "input", "options": None},
    {"name": "phone", "label": "联系电话", "data_type": "text", "form_component": "input", "options": None},
    {"name": "gender", "label": "性别", "data_type": "select", "form_component": "select", "options": ["男", "女"]},
    {"name": "village_group", "label": "村民组", "data_type": "text", "form_component": "input", "options": None},
    {"name": "birth_date", "label": "出生日期", "data_type": "date", "form_component": "date", "options": None},
    {"name": "household_no", "label": "户号", "data_type": "text", "form_component": "input", "options": None},
    {"name": "address", "label": "家庭住址", "data_type": "text", "form_component": "textarea", "options": None},
    {"name": "remark", "label": "备注", "data_type": "text", "form_component": "textarea", "options": None},
    {"name": "status", "label": "状态", "data_type": "select", "form_component": "select", "options": ["正常", "停用"]},
]

SYSTEM_MENU_TABLES = set()


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # ---------------- 系统基础表 ----------------
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS sys_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            real_name TEXT,
            role TEXT NOT NULL DEFAULT 'manager',
            phone TEXT,
            status INTEGER DEFAULT 1,
            last_login TEXT,
            create_time TEXT
        );
        CREATE TABLE IF NOT EXISTS sys_role (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_code TEXT UNIQUE NOT NULL,
            role_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sys_menu_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            parent_code TEXT,
            sort_order INTEGER DEFAULT 0,
            is_visible INTEGER DEFAULT 1,
            is_ledger INTEGER DEFAULT 0,
            table_name TEXT,
            path TEXT,
            create_time TEXT
        );
        CREATE TABLE IF NOT EXISTS sys_field_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_code TEXT NOT NULL,
            physical_field TEXT NOT NULL,
            display_label TEXT NOT NULL,
            data_type TEXT NOT NULL,
            form_component TEXT,
            is_system INTEGER DEFAULT 1,
            show_in_list INTEGER DEFAULT 1,
            show_in_form INTEGER DEFAULT 1,
            is_required INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            options_json TEXT,
            create_time TEXT,
            update_time TEXT
        );
        CREATE TABLE IF NOT EXISTS sys_field_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            label TEXT NOT NULL,
            data_type TEXT NOT NULL,
            form_component TEXT,
            options_json TEXT
        );
        CREATE TABLE IF NOT EXISTS sys_oper_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT,
            module TEXT,
            detail TEXT,
            ip TEXT,
            create_time TEXT
        );
        CREATE TABLE IF NOT EXISTS sys_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT,
            remark TEXT
        );
        CREATE TABLE IF NOT EXISTS sys_screen_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            screen_key TEXT UNIQUE NOT NULL,
            config_json TEXT,
            update_time TEXT
        );
        CREATE TABLE IF NOT EXISTS t_file_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            file_ext TEXT,
            category TEXT,
            menu_code TEXT,
            villager_name TEXT,
            related_id INTEGER,
            upload_user TEXT,
            upload_time TEXT
        );
        CREATE TABLE IF NOT EXISTS t_warning (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_code TEXT,
            ledger_name TEXT,
            item_id INTEGER,
            warning_type TEXT,
            content TEXT,
            level TEXT DEFAULT 'yellow',
            status TEXT DEFAULT 'pending',
            due_date TEXT,
            create_time TEXT,
            handle_user TEXT,
            handle_time TEXT,
            remark TEXT
        );
        """
    )
    conn.commit()

    # ---------------- 22 张业务台账表 ----------------
    for lg in LEDGERS:
        cols = ["id INTEGER PRIMARY KEY AUTOINCREMENT", "create_time TEXT", "update_time TEXT"]
        for fld in lg["fields"]:
            cols.append(f'{fld["field"]} {SQLITE_TYPE_MAP.get(fld["type"], "TEXT")}')
        create_sql = f"CREATE TABLE IF NOT EXISTS {lg['table']} ({', '.join(cols)})"
        cur.execute(create_sql)

    # ---------------- 菜单初始化 ----------------
    for m in MENUS:
        cur.execute("SELECT COUNT(*) c FROM sys_menu_config WHERE code=?", (m["code"],))
        if cur.fetchone()["c"] == 0:
            cur.execute(
                "INSERT INTO sys_menu_config(code,name,parent_code,sort_order,is_visible,is_ledger,table_name,path,create_time) VALUES(?,?,?,?,?,?,?,?,?)",
                (m["code"], m["name"], m["parent"], m["sort"], 1, m["is_ledger"], m["table"], m["path"],
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )

    # ---------------- 台账菜单 + 内置字段初始化 ----------------
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for lg in LEDGERS:
        # 台账作为二级菜单挂到一级分组下
        cur.execute("SELECT COUNT(*) c FROM sys_menu_config WHERE code=?", (lg["code"],))
        if cur.fetchone()["c"] == 0:
            cur.execute(
                "INSERT INTO sys_menu_config(code,name,parent_code,sort_order,is_visible,is_ledger,table_name,path,create_time) VALUES(?,?,?,?,?,?,?,?,?)",
                (lg["code"], lg["name"], lg["group"], lg["fields"][0]["sort_order"] if False else 1, 1, 1, lg["table"], None, now),
            )
        # 内置字段
        cur.execute("SELECT COUNT(*) c FROM sys_field_config WHERE menu_code=?", (lg["code"],))
        if cur.fetchone()["c"] == 0:
            for idx, fld in enumerate(lg["fields"]):
                cur.execute(
                    "INSERT INTO sys_field_config(menu_code,physical_field,display_label,data_type,form_component,is_system,show_in_list,show_in_form,is_required,sort_order,is_deleted,options_json,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (lg["code"], fld["field"], fld["label"], fld["type"],
                     {"text": "input", "number": "number", "date": "date", "image": "upload", "select": "select"}[fld["type"]],
                     1, 1 if fld["show_list"] else 0, 1 if fld["show_form"] else 0, 1 if fld["required"] else 0,
                     idx + 1, 0, dumps(fld["options"]) if fld["options"] else None, now, now),
                )
            # 创建时间列：需求列表展示的台账（公共列，前端动态渲染）
            if lg["code"] in ("party_member", "disabled", "low_income"):
                sort = {"party_member": 15, "disabled": 18, "low_income": 20}[lg["code"]]
                cur.execute(
                    "INSERT INTO sys_field_config(menu_code,physical_field,display_label,data_type,form_component,is_system,show_in_list,show_in_form,is_required,sort_order,is_deleted,options_json,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (lg["code"], "create_time", "创建时间", "text", "input", 1, 1, 0, 0,
                     sort, 0, None, now, now),
                )

    # ---------------- 预置字段库 ----------------
    for f in FIELD_LIBRARY:
        cur.execute("SELECT COUNT(*) c FROM sys_field_library WHERE name=?", (f["name"],))
        if cur.fetchone()["c"] == 0:
            cur.execute(
                "INSERT INTO sys_field_library(name,label,data_type,form_component,options_json) VALUES(?,?,?,?,?)",
                (f["name"], f["label"], f["data_type"], f["form_component"], dumps(f["options"]) if f["options"] else None),
            )

    # ---------------- 角色 ----------------
    roles = [(config.ROLE_ADMIN, "超级管理员"), (config.ROLE_MANAGER, "普通管理员"), (config.ROLE_VIEWER, "只读用户")]
    for code, name in roles:
        cur.execute("SELECT COUNT(*) c FROM sys_role WHERE role_code=?", (code,))
        if cur.fetchone()["c"] == 0:
            cur.execute("INSERT INTO sys_role(role_code,role_name) VALUES(?,?)", (code, name))

    # ---------------- 默认管理员 ----------------
    cur.execute("SELECT COUNT(*) c FROM sys_user WHERE username='admin'")
    if cur.fetchone()["c"] == 0:
        salt = os.urandom(8).hex()
        cur.execute(
            "INSERT INTO sys_user(username,password_hash,salt,real_name,role,phone,status,create_time) VALUES(?,?,?,?,?,?,?,?)",
            ("admin", hash_password("admin123", salt), salt, "系统管理员", config.ROLE_ADMIN, "", 1, now),
        )

    # ---------------- 系统参数 ----------------
    defaults = [
        ("village_name", "智慧乡村村委", "村名"),
        ("backup_time", "02:30", "每日自动备份时间"),
        ("backup_days", "30", "备份保留天数"),
        ("visit_warn_days", "30", "走访超期预警天数"),
        ("public_warn_days", "3", "公示到期提前提醒天数"),
        ("system_title", "智慧乡村村务综合管理系统", "系统标题"),
    ]
    for key, val, remark in defaults:
        cur.execute("SELECT COUNT(*) c FROM sys_config WHERE config_key=?", (key,))
        if cur.fetchone()["c"] == 0:
            cur.execute("INSERT INTO sys_config(config_key,config_value,remark) VALUES(?,?,?)", (key, val, remark))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("数据库初始化完成")
