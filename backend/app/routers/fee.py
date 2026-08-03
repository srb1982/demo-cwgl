import io
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..auth import get_current_user
from ..database import query_all

router = APIRouter(prefix="/api/fee", tags=["fee"])

FEE_TYPES = [
    ("medical_status", "医疗保险"),
    ("pension_status", "养老保险"),
    ("supplement_status", "大病补充"),
]

YEAR_RE = None


def _pick_year(year: str):
    if year:
        return year
    rows = query_all("SELECT DISTINCT fee_year FROM t_fee_collect WHERE fee_year IS NOT NULL AND fee_year!='' ORDER BY fee_year DESC")
    return rows[0]["fee_year"] if rows else ""


def _color(rate):
    if rate >= 80:
        return "green"
    if rate >= 50:
        return "yellow"
    return "red"


@router.get("/years")
def fee_years(user: dict = Depends(get_current_user)):
    rows = query_all("SELECT DISTINCT fee_year FROM t_fee_collect WHERE fee_year IS NOT NULL AND fee_year!='' ORDER BY fee_year DESC")
    return [r["fee_year"] for r in rows]


@router.get("/groups")
def fee_groups(user: dict = Depends(get_current_user)):
    rows = query_all("SELECT DISTINCT village_group FROM t_fee_collect WHERE village_group IS NOT NULL AND village_group!='' ORDER BY village_group")
    return [r["village_group"] for r in rows]


@router.get("/summary")
def fee_summary(year: str = "", user: dict = Depends(get_current_user)):
    y = _pick_year(year)
    rows = query_all("SELECT * FROM t_fee_collect WHERE fee_year=?", (y,)) if y else query_all("SELECT * FROM t_fee_collect")

    total = len(rows)
    per_type = {t: {"paid": 0, "unpaid": 0, "reduced": 0} for t, _ in FEE_TYPES}
    amount_total = 0.0
    for r in rows:
        amount_total += (r["amount"] or 0) or 0
        for t, _ in FEE_TYPES:
            s = r[t]
            if s == "已缴":
                per_type[t]["paid"] += 1
            elif s == "减免":
                per_type[t]["reduced"] += 1
            else:
                per_type[t]["unpaid"] += 1

    paid_cnt = sum(v["paid"] for v in per_type.values())
    unpaid_cnt = sum(v["unpaid"] for v in per_type.values())
    base = paid_cnt + unpaid_cnt
    rate = round(paid_cnt / base * 100, 1) if base else 0

    # 按村组聚合
    groups = defaultdict(lambda: {"paid": 0, "unpaid": 0, "reduced": 0, "total": 0})
    for r in rows:
        g = groups[r["village_group"] or "未分组"]
        g["total"] += 1
        for t, _ in FEE_TYPES:
            s = r[t]
            if s == "已缴":
                g["paid"] += 1
            elif s == "减免":
                g["reduced"] += 1
            else:
                g["unpaid"] += 1
    group_list = []
    for g, v in groups.items():
        b = v["paid"] + v["unpaid"]
        r = round(v["paid"] / b * 100, 1) if b else 0
        group_list.append({"group": g, "total": v["total"], "paid": v["paid"], "unpaid": v["unpaid"],
                           "reduced": v["reduced"], "rate": r, "color": _color(r)})
    group_list.sort(key=lambda x: x["rate"], reverse=True)

    return {
        "year": y,
        "overview": {
            "total": total,
            "paid": paid_cnt,
            "unpaid": unpaid_cnt,
            "reduced": sum(v["reduced"] for v in per_type.values()),
            "amount": round(amount_total, 2),
            "rate": rate,
            "color": _color(rate),
        },
        "per_type": {t: per_type[t] for t, _ in FEE_TYPES},
        "groups": group_list,
    }


@router.get("/unpaid")
def fee_unpaid(year: str = "", group: str = "", user: dict = Depends(get_current_user)):
    y = _pick_year(year)
    where, params = ["fee_year=?"], [y]
    if group:
        where.append("village_group=?")
        params.append(group)
    rows = query_all(f"SELECT * FROM t_fee_collect WHERE {' AND '.join(where)}", params)
    result = []
    for r in rows:
        missing = [name for t, name in FEE_TYPES if r[t] in (None, "", "未缴")]
        if missing:
            result.append({"id": r["id"], "name": r["name"], "village_group": r["village_group"],
                           "phone": r["phone"], "missing": "、".join(missing), "amount": r["amount"]})
    return result


@router.get("/export")
def fee_export(year: str = "", group: str = "", user: dict = Depends(get_current_user)):
    from openpyxl import Workbook
    items = fee_unpaid(year, group, user)
    wb = Workbook()
    ws = wb.active
    ws.title = "催缴名单"
    ws.append(["序号", "姓名", "村民组", "联系电话", "未缴项目", "应收金额"])
    for i, it in enumerate(items, 1):
        ws.append([i, it["name"], it["village_group"], it["phone"], it["missing"], it["amount"]])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    from urllib.parse import quote
    fname = f"催缴名单_{year or '全部'}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fname)}"})
