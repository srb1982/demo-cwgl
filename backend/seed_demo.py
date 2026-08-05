"""生成演示数据，便于预览与验收"""
import random
import sqlite3
import sys
from datetime import datetime, timedelta

sys.path.insert(0, ".")
from app.database import get_conn

random.seed(42)

SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹"
GIVEN = ["建国", "志强", "秀英", "桂兰", "玉梅", "秀兰", "桂英", "秀珍", "玉英", "国栋", "海涛", "春燕", "丽华", "卫东", "国华", "晓明", "文静", "丽丽", "军", "强", "磊", "洋", "勇", "艳", "杰", "娟", "涛", "明", "超", "秀"]

def gen_name():
    return random.choice(SURNAMES) + random.choice(["".join(random.choice(GIVEN) for _ in range(random.choice([1, 2])))])

def gen_id_card(birth):
    area = random.choice(["110101", "440111", "330102", "510105", "370102", "610103"])
    seq = f"{random.randint(0, 999):03d}"
    check = f"{random.randint(0, 9)}"
    return f"{area}{birth.strftime('%Y%m%d')}{seq}{check}"

def gen_phone():
    return f"1{random.choice(['3','5','7','8','9'])}{random.randint(100000000, 999999999)}"

def dt(*days):
    return (datetime.now() + timedelta(days=days[0])).strftime("%Y-%m-%d")

def dts(days):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

GROUPS = ["一组", "二组", "三组", "四组", "五组"]

ALL_TABLES = ["villager_info", "party_member", "disabled", "low_income", "fee_collect",
              "reservoir_migrant", "village_move", "rescue", "left_child", "elderly",
              "veteran", "oversea", "three_capital", "homestead", "drowning_prevent",
              "petition", "village_public", "public_job", "custom_rural",
              "custom_red", "custom_white",
              "rural_industry", "project", "visit_record"]

conn = get_conn()
cur = conn.cursor()

if "--reset" in sys.argv:
    for t in ALL_TABLES:
        cur.execute(f"DELETE FROM t_{t}")
    cur.execute("DELETE FROM t_warning")
    conn.commit()
    print(f"已清空 {len(ALL_TABLES)} 张台账表与预警表，开始重新生成演示数据")

# 村民信息
for i in range(120):
    birth = datetime.now() - timedelta(days=random.randint(22*365, 85*365))
    age = (datetime.now().date() - birth.date()).days // 365
    cur.execute("""INSERT INTO t_villager_info(village_group,household_no,population,householder,name,relation,gender,id_card,age,phone,address,work_type,work_address,key_mark,education,ethnic,status,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (random.choice(GROUPS), f"H{i+1:04d}", random.randint(1, 6),
         random.choice(["是", "否"]), gen_name(),
         random.choice(["本人", "配偶", "子女", "父母", "祖孙", "其他"]),
         random.choice(["男", "女"]), gen_id_card(birth), age, gen_phone(),
         f"{random.choice(GROUPS)}{random.randint(1,30)}号",
         random.choice(["在家务农", "本地务工", "县外务工", "自主创业", "无"]),
         f"{random.choice(['县内', '县外', '省外'])}{random.randint(1,50)}号",
         random.choice(["无", "低保", "残疾", "五保", "建档立卡", "优抚对象", "其他"]),
         random.choice(["文盲", "小学", "初中", "高中", "中专", "大专", "本科及以上"]),
         random.choice(["汉族", "壮族", "回族", "满族", "苗族", "维吾尔族", "彝族", "土家族", "蒙古族", "其他"]),
         random.choice(["正常", "外出", "迁出", "死亡", "已注销"]),
         random.choice(["", "外出务工", "重点关注户"]), dt(0), dt(0)))
print("村民信息 120 条")

# 党员
for i in range(18):
    birth = datetime.now() - timedelta(days=random.randint(28*365, 70*365))
    join_d = -random.randint(1, 25)*365
    positive_d = min(join_d + random.randint(0, 365), -1)
    cur.execute("""INSERT INTO t_party_member(name,gender,id_card,phone,party_branch,join_date,positive_date,fee_status,village_group,household_no,householder,age,party_age,work_address,fee_amount,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), random.choice(["男","女"]), gen_id_card(birth), gen_phone(),
         random.choice(["第一党支部","第二党支部","第三党支部"]),
         dts(join_d), dts(positive_d),
         random.choice(["正常","正常","正常","欠缴"]), random.choice(GROUPS),
         f"{random.choice(GROUPS)}{random.randint(1,30)}号", gen_name(),
         (datetime.now()-birth).days//365,
         max(0, (datetime.now() - (datetime.now() + timedelta(days=join_d))).days//365),
         random.choice(["", "", "县外务工", "自主创业"]),
         random.choice([120, 240, 300, 360, 480, 600]),
         random.choice(["", "优秀党员", "老党员"]), dt(0), dt(0)))
print("党员 18 条")

# 残疾人
for i in range(14):
    birth = datetime.now() - timedelta(days=random.randint(20*365, 75*365))
    expire = random.randint(-100, 200)
    status = "已到期" if expire < 0 else ("即将到期" if expire < 90 else "正常")
    cert_date = dts(-random.randint(1, 8)*365)
    cur.execute("""INSERT INTO t_disabled(name,gender,id_card,phone,disability_type,disability_level,certificate_no,expire_date,cert_status,village_group,household_no,householder,age,low_income,certificate_date,renew_date,guardian,guardian_phone,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), random.choice(["男","女"]), gen_id_card(birth), gen_phone(),
         random.choice(["视力","听力","言语","肢体","智力","精神","多重"]),
         random.choice(["一级","二级","三级","四级"]), f"D{random.randint(100000,999999)}",
         dts(expire), status, random.choice(GROUPS),
         f"{random.choice(GROUPS)}{random.randint(1,30)}号", gen_name(),
         (datetime.now()-birth).days//365,
         random.choice(["是","否"]), cert_date,
         dts(-random.randint(1, 4)*365),
         gen_name(), gen_phone(),
         random.choice(["", "重度残疾", "需定期随访"]), dt(0), dt(0)))
print("残疾人 14 条")

# 低保
for i in range(12):
    birth = datetime.now() - timedelta(days=random.randint(25*365, 80*365))
    cur.execute("""INSERT INTO t_low_income(name,gender,id_card,phone,household_no,householder,age,is_disabled,disability_type,disability_level,low_income_type,start_date,monthly_amount,relief_type,bank,social_card,adjust_record,end_date,status,village_group,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), random.choice(["男","女"]), gen_id_card(birth), gen_phone(), f"H{random.randint(1,9999):04d}",
         gen_name(), (datetime.now()-birth).days//365,
         random.choice(["是","否"]), random.choice(["视力","肢体","无"]), random.choice(["一级","二级","三级","四级"]),
         random.choice(["城市低保","农村低保"]), dts(-random.randint(1, 3)*365),
         random.randint(300, 1200), random.choice(["临时救助","医疗救助","教育救助","其他"]),
         random.choice(["农村信用社","农业银行","建设银行","工商银行"]),
         f"62{random.randint(1000000000000000, 9999999999999999)}",
         random.choice(["", "2026年1月保障标准上调", "2025年7月新增保障"]),
         dts(random.randint(30, 730)), random.choice(["在保","在保","在保","退出"]),
         random.choice(GROUPS), random.choice(["", "重点保障对象"]), dt(0), dt(0)))
print("低保 12 条")

# 三费收缴 - 2025/2026 年度
for year in ["2025", "2026"]:
    for i in range(90):
        birth = datetime.now() - timedelta(days=random.randint(18*365, 80*365))
        cur.execute("""INSERT INTO t_fee_collect(name,id_card,phone,village_group,fee_year,medical_status,pension_status,supplement_status,amount,household_no,family_count,householder,relation,age,identity_mark,pay_method,pay_time,operator,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (gen_name(), gen_id_card(birth), gen_phone(),
             random.choice(GROUPS), year,
             random.choices([380, 0, 0], weights=[7, 2, 1])[0],
             random.choices([300, 0, 0], weights=[6, 3, 1])[0],
             random.choices([40, 0, 0], weights=[5, 4, 1])[0],
             random.randint(200, 900),
             f"{random.choice(GROUPS)}{random.randint(1,30)}号", random.randint(1, 5),
             gen_name(), random.choice(["本人","配偶","子女","父母"]),
             (datetime.now()-birth).days//365,
             random.choice(["群众","群众","党员","低保","五保"]),
             random.choice(["微信","微信","支付宝","现金","村集体代缴"]),
             dts(-random.randint(0, 300)), random.choice(["张会计","李会计","王会计"]),
             random.choice(["", "补缴上年度"]), dt(0), dt(0)))
print("三费收缴 180 条")

# 留守儿童
for i in range(10):
    birth = datetime.now() - timedelta(days=random.randint(6*365, 14*365))
    last_visit = random.randint(-80, -5)
    cur.execute("""INSERT INTO t_left_child(village_group,household_no,name,gender,id_card,birth_date,age,school,grade,guardian_name,guardian_relation,guardian_phone,parent_name,parent_phone,work_address,left_type,care_level,last_visit_date,visit_record,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (random.choice(GROUPS), f"{random.choice(GROUPS)}{random.randint(1,30)}号", gen_name(), random.choice(["男","女"]),
         gen_id_card(birth), birth.strftime("%Y-%m-%d"), (datetime.now()-birth).days//365,
         random.choice(["村小学","镇中心小学","县实验学校"]), random.choice(["一年级","二年级","三年级","四年级","五年级","六年级"]),
         gen_name(), random.choice(["祖孙","祖孙","外祖孙","其他"]), gen_phone(),
         gen_name(), gen_phone(), f"{random.choice(['县内','县外','省外'])}务工",
         random.choice(["父母双方外出","父母一方外出","单亲留守"]), random.choice(["高","中","低"]), dts(last_visit),
         random.choice(["", "本月已走访", "需重点关注"]), random.choice(["", "学习生活正常"]), dt(0), dt(0)))
print("留守儿童 10 条")

# 老年人
for i in range(24):
    birth = datetime.now() - timedelta(days=random.randint(60*365, 95*365))
    cur.execute("""INSERT INTO t_elderly(village_group,household_no,name,gender,id_card,birth_date,age,phone,living_situation,health_status,care_type,bank_name,card_no,living_subsidy,pension_type,pension_amount,chronic_disease,emergency_contact,emergency_phone,helper,helper_phone,last_visit,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (random.choice(GROUPS), f"{random.choice(GROUPS)}{random.randint(1,30)}号", gen_name(),
         random.choice(["男","女"]), gen_id_card(birth), birth.strftime("%Y-%m-%d"), random.randint(60, 95), gen_phone(),
         random.choice(["独居","与配偶同住","与子女同住","养老机构"]),
         random.choice(["健康","一般","慢性病","半失能"]),
         random.choice(["居家养老","居家养老","集中供养"]),
         random.choice(["农村信用社","农业银行","邮政储蓄"]), f"IC{random.randint(100000000,999999999)}",
         random.choice([0, 60, 120, 150]), random.choice(["城乡居民养老","职工养老","无"]),
         random.choice([0, 100, 150, 180]), random.choice(["", "", "高血压", "糖尿病"]),
         gen_name(), gen_phone(), gen_name(), gen_phone(),
         dts(-random.randint(5, 120)), random.choice(["", "独居老人"]), dt(0), dt(0)))
print("老年人 24 条")

# 退役军人
for i in range(10):
    birth = datetime.now() - timedelta(days=random.randint(35*365, 75*365))
    cur.execute("""INSERT INTO t_veteran(village_group,household_no,householder,name,gender,id_card,age,military_type,enroll_date,discharge_date,military_years,service_type,political_status,honor_awards,subsidy_status,pension_type,phone,work_address,current_address,unit_number,discharge_no,employment_status,entrepreneurship,support_record,visit_record,annual_check_status,check_date,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (random.choice(GROUPS), f"{random.choice(GROUPS)}{random.randint(1,30)}号", gen_name(), gen_name(),
         random.choice(["男","男","女"]), gen_id_card(birth), (datetime.now()-birth).days//365,
         random.choice(["义务兵","士官","军官","志愿兵"]),
         dts(-random.randint(20, 40)*365), dts(-random.randint(5, 30)*365),
         random.randint(2, 25), random.choice(["陆军","陆军","海军","空军","武警"]),
         random.choice(["中共党员","群众","共青团员"]), random.choice(["", "", "三等功"]),
         random.choice(["正常","正常","待续办"]), random.choice(["在乡老复员军人","带病回乡退伍军人","参战退役人员","其他"]),
         gen_phone(), f"{random.choice(['县内','县外','省外'])}{random.randint(1,50)}号",
         f"{random.choice(GROUPS)}{random.randint(1,50)}号",
         f"部队{random.randint(10000,99999)}", f"TB{random.randint(100000,999999)}",
         random.choice(["公益岗位安置","自主择业","企业就业"]), random.choice(["", "养殖合作社", "小卖部"]),
         random.choice(["", "已帮扶", "申请中"]), random.choice(["", "八一走访已慰问"]),
         random.choice(["已年审","未年审"]), dts(-random.randint(10, 350)), random.choice(["", "重点优抚对象"]), dt(0), dt(0)))
print("退役军人 10 条")

# 境外人员
for i in range(6):
    cur.execute("""INSERT INTO t_oversea(village_group,household_no,householder,name,gender,id_card,age,phone,country,abroad_reason,go_abroad_date,expected_return_date,remaining_days,status,visa_no,visa_type,visa_expire_date,household_address,emergency_contact,emergency_phone,abroad_contact,regular_contact,contact_relation,abroad_unit,return_date,return_destination,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (random.choice(GROUPS), f"{random.choice(GROUPS)}{random.randint(1,30)}号", gen_name(), gen_name(),
         random.choice(["男","女"]), gen_id_card(datetime.now() - timedelta(days=random.randint(25*365, 55*365))),
         random.randint(18, 65), gen_phone(),
         random.choice(["日本","韩国","新加坡","澳大利亚","美国"]),
         random.choice(["务工","留学","经商","探亲"]),
         dts(-random.randint(100, 1000)), dts(random.randint(30, 400)), random.randint(10, 300),
         random.choice(["境外","境外","已回国","待归国"]),
         f"V{random.randint(100000,999999)}", random.choice(["工作签证","留学签证","旅游签证","探亲签证"]),
         dts(random.randint(-30, 120)), f"{random.choice(GROUPS)}{random.randint(1,50)}号",
         gen_name(), gen_phone(), f"+{random.choice(['81','82','65','61'])}{random.randint(100000000,999999999)}",
         random.choice(["是","是","否"]), random.choice(["配偶","父母","子女"]),
         f"{random.choice(['株式会社','公司','大学'])}", dts(random.randint(-60, 200)),
         random.choice(["回村务农","外出务工","定居国外"]), random.choice(["", "定期联系正常"]), dt(0), dt(0)))
print("境外人员 6 条")

# 村务公开
for i in range(8):
    expire = random.randint(-5, 20)
    cur.execute("""INSERT INTO t_village_public(public_title,publish_date,expire_date,location,status,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?)""",
        (f"{datetime.now().year}年{['第一季度财务收支','低保评议结果','危房改造名单','公益岗位聘用','村集体经济分红','党员发展对象','灌溉水费收支','新增耕地补贴'][i]}公示",
         dts(-random.randint(3, 15)), dts(expire),
         f"{random.choice(['村务公开栏','文化广场','村微信群'])}",
         "已到期" if expire < 0 else "公示中", random.choice(["", "已拍照存档"]), dt(0), dt(0)))
print("村务公开 8 条")

# 工程项目
for i in range(6):
    end_days = random.randint(-40, 90)
    cur.execute("""INSERT INTO t_project(project_name,contract_start,contract_end,contractor,budget,paid_amount,progress,acceptance_status,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (f"{['村庄道路硬化','文化广场建设','灌溉渠道维修','路灯亮化工程','人居环境整治','党群服务中心改造'][i]}",
         dts(-random.randint(30, 200)), dts(end_days),
         f"{random.choice(['市','县','镇'])}{random.choice(['建筑','市政','水利'])}工程有限公司",
         random.randint(20, 200)*10000, random.randint(10, 180)*10000,
         random.choice([0, 20, 50, 80, 100]),
         random.choice(["未验收","已验收","验收不通过"]), random.choice(["", "监理在岗"]), dt(0), dt(0)))
print("工程项目 6 条")

# 公益岗位
for i in range(10):
    end_days = random.randint(-20, 60)
    cur.execute("""INSERT INTO t_public_job(person_name,id_card,phone,job_name,area,salary,bank_name,card_no,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), gen_id_card(datetime.now() - timedelta(days=random.randint(30*365, 60*365))), gen_phone(),
         f"{random.choice(['保洁员','护林员','巡逻员','道路看护员','水管员'])}#{i+1}",
         f"{random.choice(GROUPS)}{random.choice(['主干道','河段','林区','村道'])}",
         random.choice([3600, 6000, 9600, 12000]),
         random.choice(["农村信用社","农业银行","邮政储蓄"]), f"IC{random.randint(100000000,999999999)}",
         random.choice(["", "重点路段"]), dt(0), dt(0)))
print("公益岗位 10 条")

# 防溺水
for i in range(6):
    cur.execute("""INSERT INTO t_drowning_prevent(water_area,location,patrol_person,patrol_time,hazard,rectification_status,warning_facility,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (f"{['村前河','南山水库','东湾塘','灌溉渠','荷花塘','西沟'][i]}",
         f"{['村东桥头','水库坝下','塘边竹林','渠中段','塘北岸','沟尾'][i]}",
         gen_name(), dts(-random.randint(1, 20)),
         random.choice(["", "护栏破损", "缺少警示牌", "水深坡陡"]),
         random.choice(["未整改","整改中","已整改"]),
         random.choice(["警示牌","围栏","救生圈","警示牌+围栏"]),
         random.choice(["", "重点巡查点位"]), dt(0), dt(0)))
print("防溺水 6 条")

# 信访矛盾
for i in range(6):
    cur.execute("""INSERT INTO t_petition(petitioner,phone,issue_type,content,handle_person,handle_status,handle_date,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), gen_phone(), random.choice(["土地纠纷","邻里纠纷","民生诉求"]),
         f"反映{random.choice(['宅基地边界','灌溉用水','道路出行','低保评议'])}问题",
         gen_name(), random.choice(["待处理","处理中","已办结"]),
         dts(-random.randint(1, 30)) if random.random() > 0.5 else None,
         random.choice(GROUPS), dt(0), dt(0)))
print("信访矛盾 6 条")

# 走访帮扶
for i in range(16):
    cur.execute("""INSERT INTO t_visit_record(visit_target,visit_date,visit_person,content,rectification,result,revisit_situation,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), dts(-random.randint(1, 45)), gen_name(),
         f"反映{random.choice(['生活生产','健康状况','政策落实'])}情况",
         random.choice(["", "已协调解决", "对接镇民政办"]),
         random.choice(["已办结","已办结","跟踪中"]),
         random.choice(["", "一周后回访", "电话回访"]),
         random.choice(["", "群众满意"]), dt(0), dt(0)))
print("走访帮扶 16 条")

# 乡村产业
for i in range(6):
    cur.execute("""INSERT INTO t_rural_industry(industry_type,location,production_date,owner,amount,employment_count,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?)""",
        (random.choice(["种植","养殖","加工","乡村旅游","电商"]),
         f"{random.choice(GROUPS)}{random.choice(['坡地','田间','山塘','集中连片区'])}",
         dts(-random.randint(30, 400)),
         f"{random.choice(GROUPS)}{random.choice(['合作社','家庭农场','村集体'])}",
         random.randint(10, 80)*10000, random.randint(5, 40),
         random.choice(["", "带动脱贫户务工"]), dt(0), dt(0)))
print("乡村产业 6 条")

# 三资
for i in range(8):
    cur.execute("""INSERT INTO t_three_capital(asset_name,asset_type,location,quantity,amount,status,caretaker,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (f"{['集体机井','文化活动中心','村集体林场','集体商铺','农机具','集体鱼塘','村委会办公楼','土地补偿款'][i]}",
         random.choice(["资金","资产","资源"]),
         f"{random.choice(GROUPS)}{random.choice(['村口','中心区域','山地','水塘边'])}",
         random.randint(1, 30), random.randint(5, 200)*10000,
         random.choice(["正常","正常","处置中"]), gen_name(),
         random.choice(["", "闲置待盘活"]), dt(0), dt(0)))
print("三资 8 条")

# 宅基地
for i in range(8):
    cur.execute("""INSERT INTO t_homestead(householder,village_group,build_area,apply_date,approve_status,floor_count,finish_date,illegal_build,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), random.choice(GROUPS), random.randint(80, 220),
         dts(-random.randint(20, 400)), random.choice(["待审批","已批准","建设中","已完工"]),
         random.randint(1, 3),
         dts(-random.randint(5, 200)) if random.random() > 0.3 else None,
         random.choice(["否","否","否","是"]),
         random.choice(["", "原址翻建"]), dt(0), dt(0)))
print("宅基地 8 条")

# 移风易俗（原台账数据保留）
for i in range(6):
    cur.execute("""INSERT INTO t_custom_rural(event_name,event_type,household,event_date,village_group,custom_type,create_time,update_time) VALUES(?,?,?,?,?,?,?,?)""",
        (f"{random.choice(['张府喜宴','李家白事','村集体简办婚宴'])}",
         random.choice(["红事","白事"]), gen_name(), dts(-random.randint(1, 90)),
         random.choice(GROUPS), random.choice(["简办","新办","示范引领"]), dt(0), dt(0)))
print("移风易俗 6 条")

# 移风易俗-红事统计表
for i in range(8):
    cur.execute("""INSERT INTO t_custom_red(village_group,householder,event_type,event_date,banquet_standard,wine_standard,consultant,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?)""",
        (random.choice(GROUPS), gen_name(), random.choice(["婚嫁","乔迁","满月","寿宴","升学"]),
         dts(-random.randint(1, 90)), f"{random.randint(3, 20)}桌/每桌{random.randint(300, 800)}元",
         f"{random.choice(['软中华','芙蓉王'])}每条{random.randint(400, 1000)}元",
         f"{gen_name()} 138{random.randint(10000000,99999999)}", dt(0), dt(0)))
print("红事统计表 8 条")

# 移风易俗-白事统计表
for i in range(6):
    cur.execute("""INSERT INTO t_custom_white(village_group,householder,deceased_name,deceased_time,funeral_time,banquet_standard,wine_standard,consultant,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (random.choice(GROUPS), gen_name(), gen_name(), dts(-random.randint(1, 60)),
         dts(-random.randint(0, 3)), f"{random.randint(5, 20)}桌/每桌{random.randint(200, 600)}元",
         f"{random.choice(['白酒','土酒'])}每瓶{random.randint(50, 300)}元",
         f"{gen_name()} 138{random.randint(10000000,99999999)}", dt(0), dt(0)))
print("白事统计表 6 条")

# 水库移民
for i in range(5):
    birth = datetime.now() - timedelta(days=random.randint(30*365, 70*365))
    is_dead = random.choices(["正常", "死亡", "公职人员"], weights=[8, 1, 1])[0]
    cur.execute("""INSERT INTO t_reservoir_migrant(village_group,household_no,family_count,name,gender,ethnic,relation,id_card,phone,bank_name,account_name,card_no,is_deceased,deceased_time,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (random.choice(GROUPS), f"H{random.randint(1,30):04d}", random.randint(1, 5),
         gen_name(), random.choice(["男", "女"]), random.choice(["汉族", "壮族", "其他"]),
         random.choice(["本人", "配偶", "子女", "父母"]),
         gen_id_card(birth), gen_phone(),
         random.choice(["农商行", "农业银行", "邮政储蓄", "建设银行"]),
         "存折户主", f"IC{random.randint(100000000, 999999999)}",
         is_dead,
         dts(-random.randint(30, 300)) if is_dead != "正常" else None,
         random.choice(["", "原迁安置"], ),
         dt(0), dt(0)))
print("水库移民 5 条")

# 搬迁
for i in range(6):
    cur.execute("""INSERT INTO t_village_move(village_group,household_no,householder,name,gender,id_card,age,phone,old_address,new_address,move_type,apply_date,approve_status,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (random.choice(GROUPS), f"{random.choice(GROUPS)}{random.randint(1,30)}号", gen_name(), gen_name(),
         random.choice(["男","女"]),
         gen_id_card(datetime.now() - timedelta(days=random.randint(25*365, 60*365))),
         random.randint(20, 70), gen_phone(),
         f"{random.choice(['湾里','老村','后山'])}{random.randint(1,50)}号",
         f"{random.choice(['集中安置区','镇区'])}{random.randint(1,50)}号",
         random.choice(["易地搬迁","生态搬迁","工程搬迁"]),
         dts(-random.randint(30, 200)), random.choice(["待审批","已审批","已入住","超时未办"]),
         random.choice(["", "搬迁后稳定"], ), dt(0), dt(0)))
print("搬迁 6 条")

# 救助
for i in range(10):
    cur.execute("""INSERT INTO t_rescue(village_group,householder,name,id_card,phone,rescue_type,reason,rescue_date,status,approve_date,amount,bank_name,card_no,pay_method,pay_date,operator,disease_name,disaster_type,school_grade,family_income,review_opinion,revisit_record,revisit_date,is_party,remark,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (random.choice(GROUPS), gen_name(), gen_name(),
         gen_id_card(datetime.now() - timedelta(days=random.randint(20*365, 75*365))),
         gen_phone(), random.choice(["临时救助","医疗救助","教育救助","住房救助"]),
         random.choice(["突发疾病","因灾致困","子女上学","住房困难"]),
         dts(-random.randint(30, 210)), random.choice(["申请中","已救助","已救助"]),
         dts(-random.randint(5, 180)) if random.random() > 0.3 else None,
         random.randint(500, 5000),
         random.choice(["农村信用社","农业银行","邮政储蓄"]),
         f"IC{random.randint(100000000,999999999)}",
         random.choice(["银行转账","现金","一卡通"]),
         dts(-random.randint(1, 150)) if random.random() > 0.4 else None,
         gen_name(), random.choice(["", "恶性肿瘤", "尿毒症"]), random.choice(["", "洪涝", "干旱"]),
         random.choice(["", "镇中学初一"]), random.randint(3000, 20000),
         random.choice(["", "村民代表评议通过"]), random.choice(["", "已回访，生活改善"]),
         dts(-random.randint(1, 60)) if random.random() > 0.5 else None,
         random.choice(["否","否","是"]), random.choice(["", "重点关注"]), dt(0), dt(0)))
print("救助 10 条")

conn.commit()
conn.close()
print("演示数据生成完成")
