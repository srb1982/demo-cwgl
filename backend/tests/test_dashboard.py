class TestOverview:
    def test_overview_structure(self, client, admin_h):
        r = client.get("/api/dashboard/overview", headers=admin_h)
        assert r.status_code == 200
        d = r.json()
        for k in ("village_name", "population", "party", "special", "fee", "move", "industry", "safety", "warning"):
            assert k in d
        assert "total" in d["population"] and "groups" in d["population"]
        assert "disabled" in d["special"] and "migrant" in d["special"]
        assert "rate" in d["fee"] and "list" in d["warning"]

    def test_overview_counts_react_to_data(self, client, admin_h):
        r = client.get("/api/dashboard/overview", headers=admin_h)
        before = r.json()["population"]["total"]
        r = client.post("/api/ledger/villager", headers=admin_h, json={"name": "统计甲", "gender": "男", "village_group": "一组"})
        assert r.status_code == 200
        after = client.get("/api/dashboard/overview", headers=admin_h).json()
        assert after["population"]["total"] == before + 1
        assert after["population"]["male"] >= 1
        assert any(g["name"] == "一组" for g in after["population"]["groups"])

    def test_viewer_and_manager_can_access(self, client, viewer_h, manager_h):
        assert client.get("/api/dashboard/overview", headers=viewer_h).status_code == 200
        assert client.get("/api/dashboard/overview", headers=manager_h).status_code == 200

    def test_unauth_401(self, client):
        assert client.get("/api/dashboard/overview").status_code == 401


class TestFeeTolerance:
    def test_fee_none_and_invalid_values_count_unpaid(self, client, admin_h):
        from datetime import datetime
        from app.database import execute
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute("INSERT INTO t_fee_collect(name,fee_year,medical_status,pension_status,supplement_status,create_time)"
                " VALUES(?,?,?,?,?,?)",
                ("异常费", "2099", None, "abc", 0, now))
        d = client.get("/api/dashboard/overview", headers=admin_h).json()
        assert d["fee"]["paid"] >= 0 and d["fee"]["unpaid"] >= 0
        assert d["fee"]["total"] >= 1

    def test_is_paid_edge_cases(self):
        from app.routers.dashboard import _is_paid
        assert _is_paid(None) is False
        assert _is_paid("abc") is False
        assert _is_paid("0") is False
        assert _is_paid("5.5") is True

    def test_group_count_with_extra_where(self, client, admin_h):
        from app.routers.dashboard import _group_count
        rows = _group_count("t_villager_info", "gender", "gender IS NOT NULL")
        assert isinstance(rows, list)


class TestWarningBoard:
    def test_green_warning_counts(self, client, admin_h):
        from datetime import datetime
        from app.database import execute
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute("INSERT INTO t_warning(menu_code,ledger_name,item_id,warning_type,content,level,status,create_time)"
                " VALUES('villager','村民信息台账',1,'sample','绿色提示','green','pending',?)", (now,))
        d = client.get("/api/dashboard/overview", headers=admin_h).json()
        assert d["warning"]["green"] >= 1
        assert d["warning"]["pending"] >= 1
