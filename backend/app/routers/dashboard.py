from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..config import ROLE_ADMIN, ROLE_MANAGER, ROLE_VIEWER
from ..database import query_all, query_one

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _count(table, where="", params=()):
    sql = f"SELECT COUNT(*) c FROM {table}"
    if where:
        sql += " WHERE " + where
    return query_one(sql, params)["c"]


def _group_count(table, field, extra_where="", params=()):
    sql = f'SELECT COALESCE({field},"未分组") AS name, COUNT(*) AS value FROM {table}'
    if extra_where:
        sql += " WHERE " + extra_where
    sql += f" GROUP BY {field} ORDER BY value DESC"
    return query_all(sql, params)


@router.get("/overview")
def overview(user: dict = Depends(get_current_user)):
    # 人口治理
    population = {
        "total": _count("t_villager_info"),
        "male": _count("t_villager_info", "gender='男'"),
        "female": _count("t_villager_info", "gender='女'"),
        "groups": _group_count("t_villager_info", "village_group"),
    }
    # 党建信息
    party = {
        "total": _count("t_party_member"),
        "normal": _count("t_party_member", "fee_status='正常'"),
        "owing": _count("t_party_member", "fee_status='欠缴'"),
        "groups": _group_count("t_party_member", "party_branch"),
    }
    # 特殊群体
    special = {
        "disabled": _count("t_disabled"),
        "low_income": _count("t_low_income"),
        "left_child": _count("t_left_child"),
        "elderly": _count("t_elderly"),
        "veteran": _count("t_veteran"),
        "rescue": _count("t_rescue"),
        "oversea": _count("t_oversea"),
        "migrant": _count("t_reservoir_migrant"),
    }
    # 三费收缴
    fee_rows = query_all("SELECT * FROM t_fee_collect")
    paid = sum(1 for r in fee_rows if r["medical_status"] == "已缴") + \
        sum(1 for r in fee_rows if r["pension_status"] == "已缴") + \
        sum(1 for r in fee_rows if r["supplement_status"] == "已缴")
    unpaid = sum(1 for r in fee_rows if r["medical_status"] in ("未缴", None, "")) + \
        sum(1 for r in fee_rows if r["pension_status"] in ("未缴", None, "")) + \
        sum(1 for r in fee_rows if r["supplement_status"] in ("未缴", None, ""))
    base = paid + unpaid
    fee = {"total": len(fee_rows), "paid": paid, "unpaid": unpaid, "rate": round(paid / base * 100, 1) if base else 0}
    # 搬迁安置
    move = {
        "total": _count("t_village_move"),
        "approved": _count("t_village_move", "approve_status IN ('已审批','已入住')"),
        "pending": _count("t_village_move", "approve_status='待审批'"),
    }
    # 产业项目
    industry = {
        "industry": _count("t_rural_industry"),
        "project": _count("t_project"),
        "amount": query_one("SELECT COALESCE(SUM(amount),0) a FROM t_rural_industry")["a"],
        "budget": query_one("SELECT COALESCE(SUM(budget),0) a FROM t_project")["a"],
        "types": _group_count("t_rural_industry", "industry_type"),
    }
    # 平安综治
    safety = {
        "water": _count("t_drowning_prevent"),
        "petition": _count("t_petition"),
        "petition_doing": _count("t_petition", "handle_status IN ('待处理','处理中')"),
        "public_job": _count("t_public_job"),
        "public_assets": _count("t_three_capital"),
    }
    # 预警信息
    warn_rows = query_all("SELECT level,status,COUNT(*) c FROM t_warning GROUP BY level,status")
    warning = {"red": 0, "yellow": 0, "green": 0, "pending": 0}
    for r in warn_rows:
        warning[r["level"]] = warning.get(r["level"], 0) + r["c"]
        if r["status"] == "pending":
            warning["pending"] += r["c"]
    recent_warnings = query_all("SELECT content,level,create_time FROM t_warning WHERE status='pending' ORDER BY id DESC LIMIT 10")
    warning["list"] = recent_warnings
    return {
        "village_name": (query_one("SELECT config_value FROM sys_config WHERE config_key='village_name'") or {}).get("config_value", "智慧乡村村委"),
        "population": population, "party": party, "special": special,
        "fee": fee, "move": move, "industry": industry, "safety": safety, "warning": warning,
    }
