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
    cur.execute("""INSERT INTO t_villager_info(name,gender,id_card,phone,household_no,birth_date,household_type,address,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), random.choice(["男","女"]), gen_id_card(birth), gen_phone(), f"H{i+1:04d}",
         birth.strftime("%Y-%m-%d"), random.choice(["农业户口","非农业户口"]),
         f"{random.choice(GROUPS)}{random.randint(1,30)}号", random.choice(GROUPS),
         dt(0), dt(0)))
print("村民信息 120 条")

# 党员
for i in range(18):
    birth = datetime.now() - timedelta(days=random.randint(28*365, 70*365))
    cur.execute("""INSERT INTO t_party_member(name,gender,id_card,phone,party_branch,join_date,positive_date,fee_status,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), random.choice(["男","女"]), gen_id_card(birth), gen_phone(),
         random.choice(["第一党支部","第二党支部","第三党支部"]),
         dts(-random.randint(1, 25)*365), dts(-random.randint(1, 24)*365),
         random.choice(["正常","正常","正常","欠缴"]), random.choice(GROUPS), dt(0), dt(0)))
print("党员 18 条")

# 残疾人
for i in range(14):
    birth = datetime.now() - timedelta(days=random.randint(20*365, 75*365))
    expire = random.randint(-100, 200)
    status = "已到期" if expire < 0 else ("即将到期" if expire < 90 else "正常")
    cur.execute("""INSERT INTO t_disabled(name,id_card,phone,disability_type,disability_level,certificate_no,expire_date,cert_status,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), gen_id_card(birth), gen_phone(),
         random.choice(["视力","听力","言语","肢体","智力","精神","多重"]),
         random.choice(["一级","二级","三级","四级"]), f"D{random.randint(100000,999999)}",
         dts(expire), status, random.choice(GROUPS), dt(0), dt(0)))
print("残疾人 14 条")

# 低保
for i in range(12):
    birth = datetime.now() - timedelta(days=random.randint(25*365, 80*365))
    cur.execute("""INSERT INTO t_low_income(name,id_card,phone,household_no,monthly_amount,start_date,end_date,status,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), gen_id_card(birth), gen_phone(), f"H{random.randint(1,9999):04d}",
         random.randint(300, 1200), dts(-random.randint(1, 3)*365), dts(random.randint(30, 730)),
         random.choice(["在保","在保","在保","退出"]), random.choice(GROUPS), dt(0), dt(0)))
print("低保 12 条")

# 三费收缴 - 2025/2026 年度
for year in ["2025", "2026"]:
    for i in range(90):
        cur.execute("""INSERT INTO t_fee_collect(name,id_card,phone,village_group,fee_year,medical_status,pension_status,supplement_status,amount,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (gen_name(), gen_id_card(datetime.now() - timedelta(days=random.randint(18*365, 80*365))), gen_phone(),
             random.choice(GROUPS), year,
             random.choices(["已缴","未缴","减免"], weights=[7,2,1])[0],
             random.choices(["已缴","未缴","减免"], weights=[6,3,1])[0],
             random.choices(["已缴","未缴","减免"], weights=[5,4,1])[0],
             random.randint(200, 900), dt(0), dt(0)))
print("三费收缴 180 条")

# 留守儿童
for i in range(10):
    birth = datetime.now() - timedelta(days=random.randint(6*365, 14*365))
    last_visit = random.randint(-80, -5)
    cur.execute("""INSERT INTO t_left_child(name,gender,birth_date,guardian_name,guardian_phone,school,last_visit_date,visit_status,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), random.choice(["男","女"]), birth.strftime("%Y-%m-%d"), gen_name(), gen_phone(),
         random.choice(["村小学","镇中心小学","县实验学校"]), dts(last_visit),
         "超期未走访" if last_visit < -30 else "正常", random.choice(GROUPS), dt(0), dt(0)))
print("留守儿童 10 条")

# 老年人
for i in range(24):
    birth = datetime.now() - timedelta(days=random.randint(60*365, 95*365))
    expire = random.randint(-60, 300)
    cur.execute("""INSERT INTO t_elderly(name,id_card,phone,village_group,age,subsidy_status,expire_date,care_type,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), gen_id_card(birth), gen_phone(), random.choice(GROUPS),
         random.randint(60, 95), "已停发" if expire < 0 else random.choice(["正常","待续办"]),
         dts(expire), random.choice(["居家养老","集中供养","日间照料"]), dt(0), dt(0)))
print("老年人 24 条")

# 退役军人
for i in range(10):
    birth = datetime.now() - timedelta(days=random.randint(35*365, 75*365))
    cur.execute("""INSERT INTO t_veteran(name,id_card,phone,military_type,enroll_date,discharge_date,subsidy_status,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), gen_id_card(birth), gen_phone(), random.choice(["义务兵","士官","军官","志愿兵"]),
         dts(-random.randint(20, 40)*365), dts(-random.randint(5, 30)*365),
         random.choice(["正常","正常","待续办"]), random.choice(GROUPS), dt(0), dt(0)))
print("退役军人 10 条")

# 境外人员
for i in range(6):
    cur.execute("""INSERT INTO t_oversea(name,id_card,phone,visa_no,visa_expire_date,go_abroad_date,return_date,status,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), gen_id_card(datetime.now() - timedelta(days=random.randint(25*365, 55*365))), gen_phone(),
         f"V{random.randint(100000,999999)}", dts(random.randint(-30, 120)),
         dts(-random.randint(100, 1000)), dts(random.randint(-60, 200)),
         random.choice(["境外","境外","已回国","待归国"]), random.choice(GROUPS), dt(0), dt(0)))
print("境外人员 6 条")

# 村务公开
for i in range(8):
    expire = random.randint(-5, 20)
    cur.execute("""INSERT INTO t_village_public(public_title,public_type,public_content,publish_date,expire_date,status,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?)""",
        (f"{datetime.now().year}年{['第一季度财务收支','低保评议结果','危房改造名单','公益岗位聘用','村集体经济分红','党员发展对象','灌溉水费收支','新增耕地补贴'][i]}公示",
         random.choice(["财务公开","党务公开","村务公开"]), "详细内容见村务公开栏",
         dts(-random.randint(3, 15)), dts(expire), "已到期" if expire < 0 else "公示中",
         random.choice(GROUPS), dt(0), dt(0)))
print("村务公开 8 条")

# 工程项目
for i in range(6):
    end_days = random.randint(-40, 90)
    cur.execute("""INSERT INTO t_project(project_name,project_type,budget,contractor,contract_start,contract_end,payment_node,progress,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (f"{['村庄道路硬化','文化广场建设','灌溉渠道维修','路灯亮化工程','人居环境整治','党群服务中心改造'][i]}",
         random.choice(["基础设施","公共服务","产业项目"]), random.randint(20, 200)*10000,
         f"{random.choice(['市','县','镇'])}{random.choice(['建筑','市政','水利'])}工程有限公司",
         dts(-random.randint(30, 200)), dts(end_days),
         f"按进度{random.randint(1,4)}次支付", random.choice(["筹备","施工中","验收中","已完工"]),
         random.choice(GROUPS), dt(0), dt(0)))
print("工程项目 6 条")

# 公益岗位
for i in range(10):
    end_days = random.randint(-20, 60)
    cur.execute("""INSERT INTO t_public_job(job_name,person_name,id_card,village_group,job_type,contract_start,contract_end,status,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (f"{random.choice(['保洁员','护林员','巡逻员','道路看护员','水管员'])}#{i+1}",
         gen_name(), gen_id_card(datetime.now() - timedelta(days=random.randint(30*365, 60*365))), random.choice(GROUPS),
         random.choice(["保洁","护林","巡逻","看护"]), dts(-random.randint(100, 300)), dts(end_days),
         "已离职" if end_days < 0 else "在岗", dt(0), dt(0)))
print("公益岗位 10 条")

# 防溺水
for i in range(6):
    cur.execute("""INSERT INTO t_drowning_prevent(water_area,village_group,area_type,danger_level,responsible,responsible_phone,sign_count,check_date,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (f"{['村前河','南山水库','东湾塘','灌溉渠','荷花塘','西沟'][i]}",
         random.choice(GROUPS), random.choice(["河流","水库","池塘","沟渠"]),
         random.choice(["高","中","低"]), gen_name(), gen_phone(), random.randint(2, 12),
         dts(-random.randint(1, 20)), dt(0), dt(0)))
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
    cur.execute("""INSERT INTO t_visit_record(visit_person,visit_target,visit_type,visit_date,content,village_group,helper,result,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), gen_name(), random.choice(["定期走访","节日慰问","结对帮扶","回访"]),
         dts(-random.randint(1, 45)), f"了解{random.choice(['生活生产','健康状况','政策落实'])}情况",
         random.choice(GROUPS), gen_name(), random.choice(["已解决","持续跟进","已转办"]), dt(0), dt(0)))
print("走访帮扶 16 条")

# 乡村产业
for i in range(6):
    cur.execute("""INSERT INTO t_rural_industry(project_name,industry_type,scale,amount,owner,manage_date,status,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (f"{['生态茶园','大棚蔬菜','林下养鸡','光伏发电','农产品电商','稻田养鱼'][i]}",
         random.choice(["种植","养殖","加工","乡村旅游","电商"]), f"{random.randint(20,200)}亩/户",
         random.randint(10, 80)*10000, f"{random.choice(GROUPS)}{random.choice(['合作社','家庭农场','村集体'])}",
         dts(-random.randint(30, 400)), random.choice(["运营中","建设中"]), random.choice(GROUPS), dt(0), dt(0)))
print("乡村产业 6 条")

# 三资
for i in range(8):
    cur.execute("""INSERT INTO t_three_capital(asset_name,asset_type,amount,owner,manage_date,status,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?)""",
        (f"{['集体机井','文化活动中心','村集体林场','集体商铺','农机具','集体鱼塘','村委会办公楼','土地补偿款'][i]}",
         random.choice(["资金","资产","资源"]), random.randint(5, 200)*10000,
         "村集体经济组织", dts(-random.randint(100, 1000)),
         random.choice(["正常","正常","处置中"]), random.choice(GROUPS), dt(0), dt(0)))
print("三资 8 条")

# 宅基地
for i in range(8):
    cur.execute("""INSERT INTO t_homestead(householder,id_card,land_no,build_area,apply_date,approve_status,start_date,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), gen_id_card(datetime.now() - timedelta(days=random.randint(30*365, 60*365))),
         f"Z{random.randint(100000,999999)}", random.randint(80, 220),
         dts(-random.randint(20, 400)), random.choice(["待审批","已批准","建设中","已完工"]),
         dts(-random.randint(5, 200)) if random.random() > 0.3 else None,
         random.choice(GROUPS), dt(0), dt(0)))
print("宅基地 8 条")

# 移风易俗
for i in range(6):
    cur.execute("""INSERT INTO t_custom_rural(event_name,event_type,household,event_date,village_group,custom_type,create_time,update_time) VALUES(?,?,?,?,?,?,?,?)""",
        (f"{random.choice(['张府喜宴','李家白事','村集体简办婚宴'])}",
         random.choice(["红事","白事"]), gen_name(), dts(-random.randint(1, 90)),
         random.choice(GROUPS), random.choice(["简办","新办","示范引领"]), dt(0), dt(0)))
print("移风易俗 6 条")

# 水库移民
for i in range(5):
    cur.execute("""INSERT INTO t_reservoir_migrant(name,id_card,phone,migrant_no,subsidy_amount,migrate_date,address,village_group,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), gen_id_card(datetime.now() - timedelta(days=random.randint(30*365, 70*365))),
         gen_phone(), f"Y{random.randint(100000,999999)}", random.randint(2000, 20000),
         dts(-random.randint(100, 2000)*10), f"{random.choice(GROUPS)}{random.randint(1,30)}号",
         random.choice(GROUPS), dt(0), dt(0)))
print("水库移民 5 条")

# 搬迁
for i in range(6):
    cur.execute("""INSERT INTO t_village_move(name,id_card,phone,village_group,move_type,apply_date,approve_status,settle_date,address,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), gen_id_card(datetime.now() - timedelta(days=random.randint(25*365, 60*365))),
         gen_phone(), random.choice(GROUPS), random.choice(["易地搬迁","生态搬迁","工程搬迁"]),
         dts(-random.randint(30, 200)), random.choice(["待审批","已审批","已入住","超时未办"]),
         dts(-random.randint(1, 100)) if random.random() > 0.4 else None,
         f"{random.choice(['集中安置区','镇区'])}{random.randint(1,50)}号", dt(0), dt(0)))
print("搬迁 6 条")

# 救助
for i in range(10):
    cur.execute("""INSERT INTO t_rescue(name,id_card,phone,village_group,rescue_type,reason,amount,rescue_date,status,create_time,update_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (gen_name(), gen_id_card(datetime.now() - timedelta(days=random.randint(20*365, 75*365))),
         gen_phone(), random.choice(GROUPS), random.choice(["临时救助","医疗救助","教育救助","住房救助"]),
         random.choice(["突发疾病","因灾致困","子女上学","住房困难"]),
         random.randint(500, 5000), dts(-random.randint(5, 200)), random.choice(["已救助","申请中"]), dt(0), dt(0)))
print("救助 10 条")

conn.commit()
conn.close()
print("演示数据生成完成")
