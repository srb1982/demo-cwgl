"""村民信息按户归纳与家庭人数联动模块（仅作用于 villager 台账）

家庭键：household_no（户号）
户主标志：householder 列，取值 '是' 表示户主
家庭人数：population 列，按户号成员数自动重算并覆盖手填值
单人户：户号下成员数 == 1；多人户：成员数 >= 2

联动规则：
- 新增：户号已存在则归入该户并重算人数；户号不存在则为家庭第一人，自动标记户主，人数记为 1
- 编辑：多人户户主变更户号或降级户主身份时阻断，须先完成户主交接；单人户户主可自由迁出
- 删除：多人户户主阻断删除，须先交接；单人户户主可直接删除（家庭随户消亡）
- 交接：仅互换户主标志位，家庭人数与隶属关系不变

该模块所有写操作必须与调用方处于同一事务（调用方传入 db 连接）。
"""

LEDGER_MENU = "villager"
TABLE = "t_villager_info"
HOLDER = "是"
NOT_HOLDER = "否"


def is_family_menu(menu_code: str) -> bool:
    """该台账是否启用家庭联动（仅 villager 村民信息台账）"""
    return menu_code == LEDGER_MENU


def family_members(db, household_no):
    """返回某户号下所有成员行（未指定户号返回空列表）"""
    if not household_no:
        return []
    rows = db.execute(
        f'SELECT * FROM {TABLE} WHERE household_no=? ORDER BY id',
        (str(household_no),),
    ).fetchall()
    return [dict(r) for r in rows]


def family_size(db, household_no) -> int:
    """户号下成员数"""
    return len(family_members(db, household_no))


def is_holder(member) -> bool:
    """是否为户主"""
    return bool(member) and member.get("householder") == HOLDER


def sync_population(db, household_no) -> int:
    """按户号成员数重算该户所有成员行的 population，返回户内人数"""
    members = family_members(db, household_no)
    size = len(members)
    if size:
        db.execute(
            f'UPDATE {TABLE} SET population=? WHERE household_no=?',
            (size, str(household_no)),
        )
    return size


def guard_householder_change(db, member):
    """编辑/删除校验：多人户户主不可变更户属或降级，须先交接。
    返回 (ok, message, candidates)；candidates 为可交接的成员列表（排除户主本人）。
    单人户户主与非户主一律放行。
    """
    if not is_holder(member):
        return True, None, []
    members = family_members(db, member["household_no"])
    if len(members) > 1:
        candidates = [m for m in members if m["id"] != member["id"]]
        names = "、".join(m["name"] or f"#{m['id']}" for m in candidates[:3])
        return False, (
            f"该成员是户主，家庭还有其他成员，无法直接变更户属关系。"
            f"请先将一名家庭成员（如{names}）变更为户主。"
        ), candidates
    return True, None, []
