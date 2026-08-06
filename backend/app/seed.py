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
            F("medical_status", "医疗保险", "number", True, True, True),
            F("pension_status", "养老保险", "number", True, True, True),
            F("supplement_status", "大病补充", "number", True, True, True),
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
            F("village_group", "组", "text", False, True, True),
            F("household_no", "户号", "text", False, True, True),
            F("family_count", "人口", "number", False, True, True),
            F("name", "姓名", "text", True, True, True),
            F("gender", "性别", "select", False, True, True, ["男", "女"]),
            F("ethnic", "民族", "select", False, True, True, ["汉族", "壮族", "回族", "满族", "苗族", "维吾尔族", "彝族", "土家族", "蒙古族", "其他"]),
            F("relation", "与户主关系", "select", False, True, True, ["本人", "配偶", "子女", "父母", "祖孙", "其他"]),
            F("id_card", "身份证号码", "text", True, True, True),
            F("phone", "联系电话", "text", False, True, True),
            F("bank_name", "社保卡银行名称", "text", False, True, True),
            F("account_name", "开户姓名", "text", False, True, True),
            F("card_no", "社保卡号", "text", False, True, True),
            F("is_deceased", "是否死亡/公职人员", "select", False, True, True, ["正常", "死亡", "公职人员"]),
            F("deceased_time", "死亡时间/工作时间", "date", False, True, True),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "village_move", "name": "一般搬迁台账", "table": "t_village_move", "group": "base",
        "fields": [
            F("village_group", "村民组", "text", False, True, True),
            F("household_no", "户号", "text", False, True, True),
            F("householder", "户主姓名", "text", False, True, True),
            F("name", "姓名", "text", True, True, True),
            F("gender", "性别", "select", False, True, True, ["男", "女"]),
            F("id_card", "身份证号码", "text", True, True, True),
            F("age", "年龄", "number", False, True, True),
            F("phone", "联系方式", "text", False, True, True),
            F("old_address", "原居住地址", "text", False, True, True),
            F("new_address", "现居住地址", "text", False, True, True),
            F("move_type", "搬迁类型", "select", True, True, True, ["易地搬迁", "生态搬迁", "工程搬迁", "其他"]),
            F("apply_date", "申请时间", "date", False, True, True),
            F("approve_status", "审批状态", "select", False, True, True, ["待审批", "已审批", "已入住", "超时未办"]),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "rescue", "name": "困难群众救助台账", "table": "t_rescue", "group": "civil",
        "fields": [
            F("village_group", "村民组", "text", False, True, True),
            F("householder", "户主姓名", "text", False, True, True),
            F("name", "救助对象姓名", "text", True, True, True),
            F("id_card", "身份证号码", "text", True, True, True),
            F("phone", "联系电话", "text", False, True, True),
            F("rescue_type", "救助类型", "select", True, True, True, ["临时救助", "医疗救助", "教育救助", "住房救助", "其他"]),
            F("reason", "申请事由", "text", False, True, True),
            F("rescue_date", "申请日期", "date", False, True, True),
            F("status", "审批状态", "select", False, True, True, ["申请中", "已救助", "已结束"]),
            F("approve_date", "审批日期", "date", False, True, True),
            F("amount", "救助金额（元）", "number", False, True, True),
            F("bank_name", "开户行", "text", False, True, True),
            F("card_no", "社保卡号", "text", False, True, True),
            F("pay_method", "发放方式", "select", False, True, True, ["银行转账", "现金", "一卡通", "其他"]),
            F("pay_date", "发放日期", "date", False, True, True),
            F("operator", "经办人", "text", False, True, True),
            F("disease_name", "疾病名称", "text", False, True, True),
            F("disaster_type", "灾害类型", "text", False, True, True),
            F("school_grade", "就读学校及年级", "text", False, True, True),
            F("family_income", "家庭年人均收入（元）", "number", False, True, True),
            F("review_opinion", "民主评议意见", "text", False, True, True),
            F("revisit_record", "救助后回访记录", "text", False, True, True),
            F("revisit_date", "回访日期", "date", False, True, True),
            F("is_party", "是否党员", "select", False, True, True, ["否", "是"]),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "left_child", "name": "留守儿童台账", "table": "t_left_child", "group": "civil",
        "fields": [
            F("village_group", "村民组", "text", False, True, True),
            F("household_no", "户号", "text", False, True, True),
            F("name", "姓名", "text", True, True, True),
            F("gender", "性别", "select", True, True, True, ["男", "女"]),
            F("id_card", "身份证号码", "text", True, True, True),
            F("birth_date", "出生日期", "date", False, True, True),
            F("age", "年龄", "number", False, True, True),
            F("school", "就读学校", "text", False, True, True),
            F("grade", "年级", "text", False, True, True),
            F("guardian_name", "监护人姓名", "text", True, True, True),
            F("guardian_relation", "监护关系", "text", False, True, True),
            F("guardian_phone", "监护人电话", "text", True, True, True),
            F("parent_name", "外出务工家长", "text", False, True, True),
            F("parent_phone", "家长电话", "text", False, True, True),
            F("work_address", "务工地址", "text", False, True, True),
            F("left_type", "留守类型", "select", False, True, True, ["父母双方外出", "父母一方外出", "单亲留守", "其他"]),
            F("care_level", "关爱级别", "select", False, True, True, ["高", "中", "低"]),
            F("last_visit_date", "最近走访", "date", False, True, True),
            F("visit_record", "走访记录", "text", False, True, True),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "elderly", "name": "老年人管理台账", "table": "t_elderly", "group": "civil",
        "fields": [
            F("village_group", "村民组", "text", False, True, True),
            F("household_no", "户号", "text", False, True, True),
            F("name", "姓名", "text", True, True, True),
            F("gender", "性别", "select", False, True, True, ["男", "女"]),
            F("id_card", "身份证号码", "text", True, True, True),
            F("birth_date", "出生日期", "date", False, True, True),
            F("age", "年龄", "number", False, True, True),
            F("phone", "联系电话", "text", False, True, True),
            F("living_situation", "居住情况", "select", False, True, True, ["独居", "与配偶同住", "与子女同住", "养老机构", "其他"]),
            F("health_status", "健康状况", "select", False, True, True, ["健康", "一般", "慢性病", "失能", "半失能"]),
            F("care_type", "养老方式", "select", False, True, True, ["居家养老", "集中供养", "日间照料"]),
            F("bank_name", "开户行", "text", False, True, True),
            F("card_no", "社保卡号", "text", False, True, True),
            F("living_subsidy", "生活补贴（元/月）", "number", False, True, True),
            F("pension_type", "养老保险类型", "select", False, True, True, ["城乡居民养老", "职工养老", "无"]),
            F("pension_amount", "养老金（元/月）", "number", False, True, True),
            F("chronic_disease", "慢性疾病", "text", False, True, True),
            F("emergency_contact", "紧急联系人", "text", False, True, True),
            F("emergency_phone", "紧急联系电话", "text", False, True, True),
            F("helper", "帮扶责任人", "text", False, True, True),
            F("helper_phone", "帮扶人电话", "text", False, True, True),
            F("last_visit", "最近走访", "date", False, True, True),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "veteran", "name": "现役退役军人台账", "table": "t_veteran", "group": "civil",
        "fields": [
            F("village_group", "村民组", "text", False, True, True),
            F("household_no", "户号", "text", False, True, True),
            F("householder", "户主姓名", "text", False, True, True),
            F("name", "姓名", "text", True, True, True),
            F("gender", "性别", "select", False, True, True, ["男", "女"]),
            F("id_card", "身份证号码", "text", True, True, True),
            F("age", "年龄", "number", False, True, True),
            F("military_type", "人员类别", "select", True, True, True, ["义务兵", "士官", "军官", "志愿兵"]),
            F("enroll_date", "入伍时间", "date", False, True, True),
            F("discharge_date", "退伍时间", "date", False, True, True),
            F("military_years", "军龄(年)", "number", False, True, True),
            F("service_type", "军种", "select", False, True, True, ["陆军", "海军", "空军", "火箭军", "武警", "其他"]),
            F("political_status", "政治面貌", "select", False, True, True, ["中共党员", "共青团员", "群众", "其他"]),
            F("honor_awards", "立功受奖情况", "text", False, True, True),
            F("subsidy_status", "优抚对象", "select", False, True, True, ["正常", "待续办", "已停发"]),
            F("pension_type", "优抚类别", "select", False, True, True, ["烈士遗属", "因公牺牲军人遗属", "病故军人遗属", "在乡老复员军人", "带病回乡退伍军人", "参战退役人员", "其他"]),
            F("phone", "联系方式", "text", False, True, True),
            F("work_address", "务工地址", "text", False, True, True),
            F("current_address", "现居住地址", "text", False, True, True),
            F("unit_number", "服役部队番号", "text", False, True, True),
            F("discharge_no", "退役证编号", "text", False, True, True),
            F("employment_status", "就业安置情况", "text", False, True, True),
            F("entrepreneurship", "创业情况", "text", False, True, True),
            F("support_record", "困难帮扶记录", "text", False, True, True),
            F("visit_record", "八一/春节走访记录", "text", False, True, True),
            F("annual_check_status", "年审状态", "select", False, True, True, ["已年审", "未年审"]),
            F("check_date", "审核日期", "date", False, True, True),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "oversea", "name": "境外人员台账", "table": "t_oversea", "group": "civil",
        "fields": [
            F("village_group", "村民组", "text", False, True, True),
            F("household_no", "户号", "text", False, True, True),
            F("householder", "户主姓名", "text", False, True, True),
            F("name", "姓名", "text", True, True, True),
            F("gender", "性别", "select", False, True, True, ["男", "女"]),
            F("id_card", "身份证号码", "text", True, True, True),
            F("age", "年龄", "number", False, True, True),
            F("phone", "联系电话", "text", False, True, True),
            F("country", "出境国家/地区", "text", False, True, True),
            F("abroad_reason", "出境事由", "select", False, True, True, ["务工", "留学", "经商", "探亲", "移民", "其他"]),
            F("go_abroad_date", "出境日期", "date", False, True, True),
            F("expected_return_date", "预计归国日期", "date", False, True, True),
            F("remaining_days", "剩余天数", "number", False, True, True),
            F("status", "归国状态", "select", False, True, True, ["境外", "已回国", "待归国"]),
            F("visa_no", "护照号码", "text", False, True, True),
            F("visa_type", "签证类型", "text", False, True, True),
            F("visa_expire_date", "签证有效期", "date", False, True, True),
            F("household_address", "户籍地址", "text", False, True, True),
            F("emergency_contact", "紧急联系人", "text", False, True, True),
            F("emergency_phone", "紧急联系电话", "text", False, True, True),
            F("abroad_contact", "国外联系方式", "text", False, True, True),
            F("regular_contact", "是否定期联系", "select", False, True, True, ["是", "否"]),
            F("contact_relation", "联系人关系", "text", False, True, True),
            F("abroad_unit", "境外工作单位/学校", "text", False, True, True),
            F("return_date", "实际归国日期", "date", False, True, True),
            F("return_destination", "归国后去向", "text", False, True, True),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "three_capital", "name": "三资管理台账", "table": "t_three_capital", "group": "gov",
        "fields": [
            F("asset_name", "资产名称", "text", True, True, True),
            F("asset_type", "资产类型", "select", True, True, True, ["资金", "资产", "资源"]),
            F("location", "坐落位置", "text", False, True, True),
            F("quantity", "数量", "number", False, True, True),
            F("amount", "原值(元)", "number", False, True, True),
            F("status", "使用状态", "select", False, True, True, ["正常", "处置中", "已出租"]),
            F("caretaker", "管护人", "text", False, True, True),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "homestead", "name": "宅基地建房台账", "table": "t_homestead", "group": "gov",
        "fields": [
            F("householder", "户主", "text", True, True, True),
            F("village_group", "村民组", "text", False, True, True),
            F("build_area", "确权面积(㎡)", "number", False, True, True),
            F("apply_date", "建房申请时间", "date", False, True, True),
            F("approve_status", "审批状态", "select", False, True, True, ["待审批", "已批准", "建设中", "已完工"]),
            F("floor_count", "房屋层数", "number", False, True, True),
            F("finish_date", "竣工时间", "date", False, True, True),
            F("illegal_build", "违建", "select", False, True, True, ["否", "是"]),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "drowning_prevent", "name": "防溺水综治台账", "table": "t_drowning_prevent", "group": "gov",
        "fields": [
            F("water_area", "水域名称", "text", True, True, True),
            F("location", "点位位置", "text", False, True, True),
            F("patrol_person", "巡河人员", "text", False, True, True),
            F("patrol_time", "巡河时间", "date", False, True, True),
            F("hazard", "安全隐患", "text", False, True, True),
            F("rectification_status", "整改状态", "select", False, True, True, ["未整改", "整改中", "已整改"]),
            F("warning_facility", "警示设施", "select", False, True, True, ["警示牌", "围栏", "救生圈", "警示牌+围栏", "无"]),
            F("remark", "备注", "text", False, True, True),
        ],
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
            F("public_title", "公开事项", "text", True, True, True),
            F("publish_date", "公示开始", "date", True, True, True),
            F("expire_date", "公示结束", "date", False, True, True),
            F("location", "公示地点", "text", False, True, True),
            F("status", "到期状态", "select", False, True, True, ["公示中", "已到期"]),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "public_job", "name": "公益性岗位台账", "table": "t_public_job", "group": "gov",
        "fields": [
            F("person_name", "姓名", "text", True, True, True),
            F("id_card", "身份证号码", "text", False, True, True),
            F("phone", "联系电话", "text", False, True, True),
            F("job_name", "岗位名称", "text", True, True, True),
            F("area", "责任片区", "text", False, True, True),
            F("salary", "工资（元/年）", "number", False, True, True),
            F("bank_name", "开户行", "text", False, True, True),
            F("card_no", "社保卡号", "text", False, True, True),
            F("remark", "备注", "text", False, True, True),
        ],
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
        "code": "custom_red", "name": "移风易俗-红事统计表", "table": "t_custom_red", "group": "gov",
        "fields": [
            F("village_group", "村名", "text", False, True, True),
            F("householder", "户主", "text", False, True, True),
            F("event_type", "红事类别", "select", False, True, True, ["婚嫁", "乔迁", "满月", "寿宴", "升学", "其他"]),
            F("event_date", "办事时间", "date", False, True, True),
            F("banquet_standard", "宴席标准(桌/价格)", "text", False, True, True),
            F("wine_standard", "烟酒标准(价格)", "text", False, True, True),
            F("consultant", "看日子先生及电话号码", "text", False, True, True),
        ],
    },
    {
        "code": "custom_white", "name": "移风易俗-白事统计表", "table": "t_custom_white", "group": "gov",
        "fields": [
            F("village_group", "村名", "text", False, True, True),
            F("householder", "户主", "text", False, True, True),
            F("deceased_name", "去世人员", "text", False, True, True),
            F("deceased_time", "去世时间", "date", False, True, True),
            F("funeral_time", "出殡时间", "date", False, True, True),
            F("banquet_standard", "宴席标准(桌/价格)", "text", False, True, True),
            F("wine_standard", "烟酒标准(价格)", "text", False, True, True),
            F("consultant", "看日子先生及电话号码", "text", False, True, True),
        ],
    },
    {
        "code": "rural_industry", "name": "乡村产业台账", "table": "t_rural_industry", "group": "gov",
        "fields": [
            F("industry_type", "产业类型", "select", True, True, True, ["种植", "养殖", "加工", "乡村旅游", "电商"]),
            F("location", "地块位置", "text", False, True, True),
            F("production_date", "投产时间", "date", False, True, True),
            F("owner", "负责人", "text", False, True, True),
            F("amount", "年度收益(元)", "number", False, True, True),
            F("employment_count", "带动就业人数", "number", False, True, True),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "project", "name": "工程项目台账", "table": "t_project", "group": "gov",
        "fields": [
            F("project_name", "项目名称", "text", True, True, True),
            F("contract_start", "开工时间", "date", False, True, True),
            F("contract_end", "竣工时间", "date", False, True, True),
            F("contractor", "施工单位", "text", False, True, True),
            F("budget", "总预算(元)", "number", False, True, True),
            F("paid_amount", "已支付(元)", "number", False, True, True),
            F("progress", "工程进度(%)", "number", False, True, True),
            F("acceptance_status", "验收状态", "select", False, True, True, ["未验收", "已验收", "验收不通过"]),
            F("remark", "备注", "text", False, True, True),
        ],
    },
    {
        "code": "visit_record", "name": "走访帮扶台账", "table": "t_visit_record", "group": "gov",
        "fields": [
            F("visit_target", "走访对象", "text", True, True, True),
            F("visit_date", "走访时间", "date", True, True, True),
            F("visit_person", "走访人员", "text", True, True, True),
            F("content", "群众诉求", "text", False, True, True),
            F("rectification", "整改措施", "text", False, True, True),
            F("result", "办结状态", "text", False, True, True),
            F("revisit_situation", "回访情况", "text", False, True, True),
            F("remark", "备注", "text", False, True, True),
        ],
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
            # 创建时间列：公共列（前端动态渲染），veteran/oversea 需求未含创建时间列
            if lg["code"] not in ("veteran", "oversea"):
                show_ct = 0 if lg["code"] in ("custom_red", "custom_white") else 1
                cur.execute(
                    "INSERT INTO sys_field_config(menu_code,physical_field,display_label,data_type,form_component,is_system,show_in_list,show_in_form,is_required,sort_order,is_deleted,options_json,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (lg["code"], "create_time", "创建时间", "text", "input", 1, show_ct, 0, 0,
                     len(lg["fields"]) + 1, 0, None, now, now),
                )

    # ---------------- 预置字段库 ----------------
    for f in FIELD_LIBRARY:
        cur.execute("SELECT COUNT(*) c FROM sys_field_library WHERE name=?", (f["name"],))
        if cur.fetchone()["c"] == 0:
            cur.execute(
                "INSERT INTO sys_field_library(name,label,data_type,form_component,options_json) VALUES(?,?,?,?,?)",
                (f["name"], f["label"], f["data_type"], f["form_component"], dumps(f["options"]) if f["options"] else None),
            )

    # ---------------- 原移风易俗台账菜单隐藏（数据保留，红事/白事替代） ----------------
    cur.execute("UPDATE sys_menu_config SET is_visible=0 WHERE code='custom_rural' AND is_visible=1")

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
