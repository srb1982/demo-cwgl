import io
import uuid

import pytest
from openpyxl import Workbook

H_NO = lambda: f"TH{uuid.uuid4().hex[:8].upper()}"  # noqa: E731


@pytest.fixture(scope="module")
def mgr(client, manager_h):
    return client, manager_h


def _create(client, headers, name, household_no, **extra):
    item = {"name": name, "household_no": household_no}
    item.update(extra)
    r = client.post("/api/ledger/villager", json=item, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _detail(client, headers, item_id):
    r = client.get(f"/api/ledger/villager/detail/{item_id}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["item"]


def _update(client, headers, item_id, **fields):
    return client.put(f"/api/ledger/villager/{item_id}", json=fields, headers=headers)


def _delete(client, headers, item_id):
    return client.delete(f"/api/ledger/villager/{item_id}", headers=headers)


def _xlsx(headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _import(client, headers, rows):
    data = _xlsx(["姓名", "户号", "户主"], rows)
    r = client.post("/api/ledger/villager/import", headers=headers,
                    files={"file": ("导入.xlsx", data,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 200, r.text
    return r.json()


class TestFamilyAutoInduce:
    """新增：自动归纳与人数联动"""

    def test_first_member_auto_holder_population_1(self, client, manager_h):
        hno = H_NO()
        mid = _create(client, manager_h, "家人甲", hno)
        row = _detail(client, manager_h, mid)
        assert row["householder"] == "是"
        assert row["population"] == 1

    def test_join_existing_family_recalc(self, client, manager_h):
        hno = H_NO()
        a = _create(client, manager_h, "家人乙", hno)
        b = _create(client, manager_h, "家人丙", hno)
        for iid in (a, b):
            assert _detail(client, manager_h, iid)["population"] == 2

    def test_join_existing_family_explicit_not_holder(self, client, manager_h):
        hno = H_NO()
        a = _create(client, manager_h, "家人丁", hno)
        b = _create(client, manager_h, "家人戊", hno, householder="否")
        row_b = _detail(client, manager_h, b)
        assert row_b["householder"] == "否"
        assert row_b["population"] == 2
        assert _detail(client, manager_h, a)["population"] == 2


class TestFamilyEdit:
    """编辑：变更户属关系"""

    def test_regular_member_move_out_recalc(self, client, manager_h):
        h1, h2 = H_NO(), H_NO()
        a = _create(client, manager_h, "成员1", h1)
        b = _create(client, manager_h, "成员2", h1)
        c = _create(client, manager_h, "成员3", h2)
        r = _update(client, manager_h, b, household_no=h2, householder="否")
        assert r.status_code == 200, r.text
        assert _detail(client, manager_h, a)["population"] == 1
        assert _detail(client, manager_h, c)["population"] == 2
        assert _detail(client, manager_h, b)["population"] == 2

    def test_multi_holder_change_household_blocked(self, client, manager_h):
        h1, h2 = H_NO(), H_NO()
        a = _create(client, manager_h, "户主1", h1)
        _create(client, manager_h, "成员11", h1)
        r = _update(client, manager_h, a, household_no=h2)
        assert r.status_code == 400
        assert "户主" in r.json()["detail"]
        assert _detail(client, manager_h, a)["household_no"] == h1

    def test_multi_holder_demote_blocked(self, client, manager_h):
        h1 = H_NO()
        a = _create(client, manager_h, "户主2", h1)
        _create(client, manager_h, "成员21", h1)
        r = _update(client, manager_h, a, householder="否")
        assert r.status_code == 400
        assert "户主" in r.json()["detail"]
        assert _detail(client, manager_h, a)["householder"] == "是"

    def test_single_holder_merge_into_other_family(self, client, manager_h):
        h1, h2 = H_NO(), H_NO()
        a = _create(client, manager_h, "独户主", h1)
        b = _create(client, manager_h, "他人1", h2)
        _create(client, manager_h, "他人2", h2)
        r = _update(client, manager_h, a, household_no=h2, householder="否")
        assert r.status_code == 200, r.text
        row_a = _detail(client, manager_h, a)
        assert row_a["householder"] == "否"
        assert row_a["population"] == 3
        assert _detail(client, manager_h, b)["population"] == 3

    def test_regular_member_promote_demotes_old_holder(self, client, manager_h):
        h1 = H_NO()
        a = _create(client, manager_h, "原户主", h1)
        b = _create(client, manager_h, "候补", h1, householder="否")
        r = _update(client, manager_h, b, householder="是")
        assert r.status_code == 200, r.text
        assert _detail(client, manager_h, a)["householder"] == "否"
        assert _detail(client, manager_h, b)["householder"] == "是"
        assert _detail(client, manager_h, a)["population"] == 2


class TestFamilyDelete:
    """删除：户主删除的两条路径"""

    def test_delete_single_holder_ok(self, client, manager_h):
        hno = H_NO()
        a = _create(client, manager_h, "独居户主", hno)
        r = _delete(client, manager_h, a)
        assert r.status_code == 200, r.text
        assert client.get(f"/api/ledger/villager/detail/{a}", headers=manager_h).status_code == 404

    def test_delete_multi_holder_blocked(self, client, manager_h):
        hno = H_NO()
        a = _create(client, manager_h, "户主3", hno)
        b = _create(client, manager_h, "成员3", hno)
        r = _delete(client, manager_h, a)
        assert r.status_code == 400
        assert "户主" in r.json()["detail"]
        assert _detail(client, manager_h, b)["population"] == 2

    def test_delete_regular_member_recalc(self, client, manager_h):
        hno = H_NO()
        a = _create(client, manager_h, "户主4", hno)
        b = _create(client, manager_h, "成员4", hno)
        c = _create(client, manager_h, "成员5", hno)
        r = _delete(client, manager_h, b)
        assert r.status_code == 200, r.text
        assert _detail(client, manager_h, a)["population"] == 2
        assert _detail(client, manager_h, c)["population"] == 2

    def test_blocked_delete_leaves_data_untouched(self, client, manager_h):
        hno = H_NO()
        a = _create(client, manager_h, "户主5", hno)
        b = _create(client, manager_h, "成员6", hno)
        _delete(client, manager_h, a)
        assert _detail(client, manager_h, a)["householder"] == "是"
        assert _detail(client, manager_h, b)["population"] == 2


class TestTransferHouseholder:
    """户主交接接口"""

    def test_transfer_swaps_holder_flag_only(self, client, manager_h):
        hno = H_NO()
        a = _create(client, manager_h, "旧户主", hno)
        b = _create(client, manager_h, "新户主", hno, householder="否")
        r = client.post("/api/ledger/villager/transfer-householder",
                        json={"household_no": hno, "current_holder_id": a, "new_holder_id": b},
                        headers=manager_h)
        assert r.status_code == 200, r.text
        assert _detail(client, manager_h, a)["householder"] == "否"
        assert _detail(client, manager_h, b)["householder"] == "是"
        assert _detail(client, manager_h, a)["population"] == 2
        assert _detail(client, manager_h, b)["population"] == 2

    def test_transfer_requires_holder(self, client, manager_h):
        hno = H_NO()
        a = _create(client, manager_h, "户主A", hno)
        b = _create(client, manager_h, "成员B", hno, householder="否")
        c = _create(client, manager_h, "成员C", hno, householder="否")
        r = client.post("/api/ledger/villager/transfer-householder",
                        json={"household_no": hno, "current_holder_id": b, "new_holder_id": c},
                        headers=manager_h)
        assert r.status_code == 400

    def test_transfer_member_must_be_in_family(self, client, manager_h):
        hno = H_NO()
        other = H_NO()
        a = _create(client, manager_h, "户主X", hno)
        outsider = _create(client, manager_h, "外人X", other)
        r = client.post("/api/ledger/villager/transfer-householder",
                        json={"household_no": hno, "current_holder_id": a, "new_holder_id": outsider},
                        headers=manager_h)
        assert r.status_code == 400

    def test_transfer_to_self_blocked(self, client, manager_h):
        hno = H_NO()
        a = _create(client, manager_h, "户主Y", hno)
        r = client.post("/api/ledger/villager/transfer-householder",
                        json={"household_no": hno, "current_holder_id": a, "new_holder_id": a},
                        headers=manager_h)
        assert r.status_code == 400


class TestHouseholdCheck:
    """家庭信息查询接口"""

    def test_household_check(self, client, manager_h):
        hno = H_NO()
        a = _create(client, manager_h, "户主Z", hno)
        b = _create(client, manager_h, "成员Z", hno, householder="否")
        r = client.get(f"/api/ledger/villager/household-check",
                       params={"household_no": hno}, headers=manager_h)
        assert r.status_code == 200
        data = r.json()
        assert data["enabled"] is True
        assert data["size"] == 2
        assert data["is_single"] is False
        assert data["holder"]["id"] == a
        assert {m["id"] for m in data["members"]} == {a, b}

    def test_household_check_exclude_id(self, client, manager_h):
        hno = H_NO()
        a = _create(client, manager_h, "户主W", hno)
        b = _create(client, manager_h, "成员W", hno, householder="否")
        r = client.get(f"/api/ledger/villager/household-check",
                       params={"household_no": hno, "exclude_id": a}, headers=manager_h)
        assert r.status_code == 200
        data = r.json()
        assert data["size"] == 2
        assert {m["id"] for m in data["members"]} == {b}

    def test_household_check_single(self, client, manager_h):
        hno = H_NO()
        _create(client, manager_h, "独户", hno)
        r = client.get(f"/api/ledger/villager/household-check",
                       params={"household_no": hno}, headers=manager_h)
        data = r.json()
        assert data["is_single"] is True
        assert data["size"] == 1


class TestFamilyImport:
    """批量导入：人口数联动"""

    def _by_name(self, client, headers, name):
        r = client.get("/api/ledger/villager", params={"keyword": name}, headers=headers)
        assert r.status_code == 200, r.text
        for it in r.json()["list"]:
            if it.get("name") == name:
                return it
        return None

    def test_import_same_household_recalc(self, client, manager_h):
        hno = H_NO()
        names = [f"导入户A{uuid.uuid4().hex[:4]}", f"导入户B{uuid.uuid4().hex[:4]}"]
        _import(client, manager_h, [[names[0], hno, "是"], [names[1], hno, "否"]])
        for n in names:
            row = self._by_name(client, manager_h, n)
            assert row is not None
            assert row["population"] == 2

    def test_import_new_household_single(self, client, manager_h):
        hno = H_NO()
        n = f"导入独户{uuid.uuid4().hex[:4]}"
        _import(client, manager_h, [[n, hno, "是"]])
        row = self._by_name(client, manager_h, n)
        assert row["population"] == 1

    def test_import_extends_existing_family(self, client, manager_h):
        hno = H_NO()
        a = _create(client, manager_h, "原住甲", hno)
        n = f"导入新成员{uuid.uuid4().hex[:4]}"
        _import(client, manager_h, [[n, hno, "否"]])
        assert _detail(client, manager_h, a)["population"] == 2
        assert self._by_name(client, manager_h, n)["population"] == 2


class TestOtherLedgersUnaffected:
    """非 villager 台账不受家庭联动影响"""

    def test_household_check_disabled_for_fee(self, client, manager_h):
        r = client.get("/api/ledger/fee_collect/household-check",
                       params={"household_no": "F0001"}, headers=manager_h)
        assert r.status_code == 200
        assert r.json()["enabled"] is False

    def test_delete_regular_ledger_no_guard(self, client, manager_h):
        r = client.post("/api/ledger/fee_collect", json={"name": f"费{uuid.uuid4().hex[:6]}"},
                        headers=manager_h)
        assert r.status_code == 200, r.text
        iid = r.json()["id"]
        r2 = client.delete(f"/api/ledger/fee_collect/{iid}", headers=manager_h)
        assert r2.status_code == 200, r2.text

    def test_transfer_rejected_for_other_ledger(self, client, manager_h):
        r = client.post("/api/ledger/fee_collect/transfer-householder",
                        json={"household_no": "F0002", "current_holder_id": 1, "new_holder_id": 2},
                        headers=manager_h)
        assert r.status_code == 400
