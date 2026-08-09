import uuid

MENU = "fee_collect"
YEAR = "2024"


def _uniq(prefix):
    return f"{prefix}{uuid.uuid4().hex[:4]}"


def _mk_fee(client, headers, **kw):
    payload = {"name": _uniq("费"), "id_card": "11010119900101" + uuid.uuid4().hex[:4].upper(),
               "fee_year": YEAR, "medical_status": 0, "pension_status": 0, "supplement_status": 0,
               "amount": 0, "village_group": "一组"}
    payload.update({k: v for k, v in kw.items() if v is not None})
    r = client.post(f"/api/ledger/{MENU}", headers=headers, json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]


class TestMeta:
    def test_years_and_groups(self, client, admin_h):
        _mk_fee(client, admin_h, fee_year=YEAR, village_group="一组")
        r = client.get("/api/fee/years", headers=admin_h)
        assert r.status_code == 200
        assert YEAR in r.json()
        groups = client.get("/api/fee/groups", headers=admin_h).json()
        assert "一组" in groups


class TestSummary:
    def test_summary_counts(self, client, admin_h):
        y = _uniq("Y")
        _mk_fee(client, admin_h, fee_year=y, village_group="一组",
                medical_status=300, pension_status=300, supplement_status=100, amount=700)
        _mk_fee(client, admin_h, fee_year=y, village_group="二组")
        r = client.get(f"/api/fee/summary?year={y}", headers=admin_h)
        assert r.status_code == 200
        ov = r.json()["overview"]
        assert ov["total"] == 2
        assert ov["paid"] == 3 and ov["unpaid"] == 3
        assert ov["rate"] == 50.0
        assert ov["color"] == "yellow"

    def test_per_type(self, client, admin_h):
        y = _uniq("Y")
        _mk_fee(client, admin_h, fee_year=y, medical_status=300, pension_status=0, supplement_status=100)
        r = client.get(f"/api/fee/summary?year={y}", headers=admin_h)
        per = r.json()["per_type"]
        assert per["medical_status"]["paid"] == 1
        assert per["pension_status"]["unpaid"] == 1

    def test_groups_aggregate(self, client, admin_h):
        y = _uniq("Y")
        gname = _uniq("组")
        _mk_fee(client, admin_h, fee_year=y, village_group=gname, medical_status=100, pension_status=100, supplement_status=100)
        r = client.get(f"/api/fee/summary?year={y}", headers=admin_h)
        g = next(x for x in r.json()["groups"] if x["group"] == gname)
        assert g["total"] == 1 and g["paid"] == 3 and g["rate"] == 100.0
        assert g["color"] == "green"

    def test_empty_db(self, client, admin_h):
        r = client.get("/api/fee/summary?year=1999", headers=admin_h)
        assert r.status_code == 200
        assert r.json()["overview"]["total"] == 0
        assert r.json()["overview"]["rate"] == 0


class TestUnpaid:
    def test_unpaid_lists_missing(self, client, admin_h):
        uniq = _uniq("欠")
        _mk_fee(client, admin_h, name=uniq, village_group="二组", pension_status=0)
        r = client.get(f"/api/fee/unpaid?year={YEAR}", headers=admin_h)
        rows = [x for x in r.json() if x["name"] == uniq]
        assert rows
        assert "养老保险" in rows[0]["missing"]

    def test_unpaid_group_filter(self, client, admin_h):
        _mk_fee(client, admin_h, village_group="五组")
        r = client.get(f"/api/fee/unpaid?year={YEAR}&group=五组", headers=admin_h)
        assert all(x["village_group"] == "五组" for x in r.json())


class TestExport:
    def test_export_xlsx(self, client, admin_h):
        r = client.get(f"/api/fee/export?year={YEAR}", headers=admin_h)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers["content-type"]
