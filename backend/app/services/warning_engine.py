"""智能预警引擎：每日扫描台账数据生成待办预警"""
from datetime import datetime, date

from ..database import get_db, query_all, query_one

LEDGERS = {
    "disabled": ("残疾人台账", "t_disabled", "name"),
    "party_member": ("党员台账", "t_party_member", "name"),
    "elderly": ("老年人台账", "t_elderly", "name"),
    "left_child": ("留守儿童台账", "t_left_child", "name"),
    "village_public": ("村务公开台账", "t_village_public", "public_title"),
    "project": ("工程项目台账", "t_project", "project_name"),
    "public_job": ("公益性岗位台账", "t_public_job", "person_name"),
    "oversea": ("境外人员台账", "t_oversea", "name"),
    "village_move": ("搬迁台账", "t_village_move", "name"),
    "fee_collect": ("三费收缴台账", "t_fee_collect", "name"),
}


def _days_to(s: str) -> int | None:
    if not s:
        return None
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
        return (d - date.today()).days
    except Exception:
        return None


def scan_all() -> dict:
    """执行全量预警扫描，返回新增与已解决数量"""
    current = set()  # (menu_code, item_id, warning_type)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def add(menu, item_id, wtype, content, level, due=None):
        current.add((menu, item_id, wtype))
        return menu, item_id, wtype, content, level, due

    pending_list = []
    with get_db() as db:
        for code, (lname, table, name_field) in LEDGERS.items():
            try:
                rows = db.execute(f"SELECT id,{name_field} AS nm,* FROM {table}").fetchall()
            except Exception:
                continue
            for r in rows:
                rid = r["id"]
                nm = r["nm"] or f"记录#{rid}"
                # 残疾证到期
                if code == "disabled":
                    d = _days_to(r["expire_date"])
                    if d is not None and d <= 0:
                        pending_list.append(add(code, rid, "cert_expire", f"【{nm}】残疾证已于 {r['expire_date']} 到期，请及时换证", "red", r["expire_date"]))
                    elif d is not None and d <= 90:
                        pending_list.append(add(code, rid, "cert_expire", f"【{nm}】残疾证将于 {r['expire_date']} 到期（剩余{d}天），请安排换证", "yellow", r["expire_date"]))
                # 党员转正/党费
                if code == "party_member":
                    if r["fee_status"] == "欠缴":
                        pending_list.append(add(code, rid, "party_fee", f"【{nm}】党费存在欠缴，请提醒补缴", "yellow"))
                    d = _days_to(r["join_date"])
                    if d is not None and d < -365 and not r["positive_date"]:
                        pending_list.append(add(code, rid, "party_positive", f"【{nm}】预备党员入党已超一年尚未转正，请办理转正手续", "yellow"))
                # 高龄补贴到期
                if code == "elderly":
                    d = _days_to(r["expire_date"])
                    if d is not None and d <= 0:
                        pending_list.append(add(code, rid, "subsidy_expire", f"【{nm}】高龄补贴已到期（{r['expire_date']}），请办理续领", "red", r["expire_date"]))
                    elif d is not None and d <= 60:
                        pending_list.append(add(code, rid, "subsidy_expire", f"【{nm}】高龄补贴将于 {r['expire_date']} 到期（剩余{d}天）", "yellow", r["expire_date"]))
                # 留守儿童超期未走访
                if code == "left_child":
                    d = _days_to(r["last_visit_date"])
                    if d is not None and d < -30:
                        pending_list.append(add(code, rid, "visit_overdue", f"【{nm}】留守儿童已 {abs(d)} 天未走访（最近走访 {r['last_visit_date']}）", "yellow"))
                # 村务公示到期
                if code == "village_public":
                    d = _days_to(r["expire_date"])
                    if d is not None and d <= 0:
                        pending_list.append(add(code, rid, "public_expire", f"【{nm}】村务公示已到期（{r['expire_date']}），请办理下期公示", "yellow", r["expire_date"]))
                    elif d is not None and d <= 3:
                        pending_list.append(add(code, rid, "public_expire", f"【{nm}】村务公示将于 {r['expire_date']} 到期（剩余{d}天）", "yellow", r["expire_date"]))
                # 工程项目节点
                if code == "project":
                    d = _days_to(r["contract_end"])
                    if d is not None and d <= 0:
                        pending_list.append(add(code, rid, "project_deadline", f"【{nm}】工程项目合同已于 {r['contract_end']} 到期，请核查工期与款项", "red", r["contract_end"]))
                    elif d is not None and d <= 30:
                        pending_list.append(add(code, rid, "project_deadline", f"【{nm}】工程项目合同将于 {r['contract_end']} 到期（剩余{d}天），请关注支付节点", "yellow", r["contract_end"]))
                # 公益岗位续签
                if code == "public_job":
                    d = _days_to(r["contract_end"])
                    if d is not None and d <= 0:
                        pending_list.append(add(code, rid, "job_renew", f"【{nm}】公益岗位合同已到期（{r['contract_end']}），请办理续签", "yellow", r["contract_end"]))
                    elif d is not None and d <= 30:
                        pending_list.append(add(code, rid, "job_renew", f"【{nm}】公益岗位合同将于 {r['contract_end']} 到期（剩余{d}天），请安排续签", "yellow", r["contract_end"]))
                # 境外人员
                if code == "oversea":
                    d = _days_to(r["visa_expire_date"])
                    if d is not None and d <= 0:
                        pending_list.append(add(code, rid, "visa_expire", f"【{nm}】签证已到期（{r['visa_expire_date']}），请提醒办理延期或归国", "red", r["visa_expire_date"]))
                    elif d is not None and d <= 30:
                        pending_list.append(add(code, rid, "visa_expire", f"【{nm}】签证将于 {r['visa_expire_date']} 到期（剩余{d}天）", "yellow", r["visa_expire_date"]))
                    rdt = _days_to(r["return_date"])
                    if rdt is not None and rdt < 0 and r["status"] != "已回国":
                        pending_list.append(add(code, rid, "return_remind", f"【{nm}】计划回国日期 {r['return_date']} 已过，请确认归国情况", "yellow", r["return_date"]))
                # 搬迁审批超时
                if code == "village_move":
                    d = _days_to(r["apply_date"])
                    if d is not None and d < -90 and r["approve_status"] in ("待审批", "超时未办"):
                        pending_list.append(add(code, rid, "move_approve", f"【{nm}】搬迁申请于 {r['apply_date']} 提交已超过90天，审批超时请处理", "yellow"))
                # 三费收缴：按人聚合未缴项，任一未缴生成催缴预警
                if code == "fee_collect":
                    unpaid = [fn for fn, amt in (("医疗保险", r["medical_status"]),
                                                 ("养老保险", r["pension_status"]),
                                                 ("大病补充", r["supplement_status"]))
                              if not amt or str(amt).strip() in ("0", "0.0", "")]
                    if unpaid:
                        pending_list.append(add(code, rid, "fee_unpaid",
                                                f"【{r['fee_year']}】{nm} 未缴纳{'、'.join(unpaid)}，请通知户主及时缴费", "yellow"))

        current_set = current
        # 读取现有 pending 预警
        existing = db.execute("SELECT id,menu_code,item_id,warning_type FROM t_warning WHERE status='pending'").fetchall()
        exist_keys = {(e["menu_code"], e["item_id"], e["warning_type"]) for e in existing}
        old_by_key = {(e["menu_code"], e["item_id"], e["warning_type"]): e for e in existing}

        added = 0
        resolved = 0
        for menu, item_id, wtype, content, level, due in pending_list:
            key = (menu, item_id, wtype)
            if key in exist_keys:
                continue
            db.execute(
                "INSERT INTO t_warning(menu_code,ledger_name,item_id,warning_type,content,level,status,due_date,create_time) VALUES(?,?,?,?,?,?,?,?,?)",
                (menu, LEDGERS[menu][0], item_id, wtype, content, level, "pending", due, now),
            )
            added += 1
        # 已解决的自动关闭
        for key, e in old_by_key.items():
            if key not in current_set:
                db.execute("UPDATE t_warning SET status='resolved',handle_time=?,handle_user='系统',remark='条件已恢复，自动办结' WHERE id=?",
                           (now, e["id"]))
                resolved += 1
    return {"added": added, "resolved": resolved, "pending": len(current_set)}
