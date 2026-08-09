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
