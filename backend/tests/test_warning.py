from datetime import datetime

from app.database import execute, query_one


def _mk_warning(menu="villager", level="yellow", status="pending", content="预警内容", **kw):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute(
        "INSERT INTO t_warning(menu_code,ledger_name,item_id,warning_type,content,level,status,due_date,create_time) VALUES(?,?,?,?,?,?,?,?,?)",
        (menu, "村民台账", 1, "periodic", content, level, status, "2024-12-31", now),
    )
    return query_one("SELECT id FROM t_warning ORDER BY id DESC")["id"]


def _reset_warnings():
    execute("DELETE FROM t_warning")


class TestList:
    def test_list_empty(self, client, admin_h):
        _reset_warnings()
        r = client.get("/api/warnings", headers=admin_h)
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["list"] == []

    def test_list_filter_status_level_keyword(self, client, admin_h):
        _reset_warnings()
        _mk_warning(level="red", status="pending", content="红色紧急预警")
        _mk_warning(level="yellow", status="handled", content="黄色已办结")
        r = client.get("/api/warnings?level=red&status=pending", headers=admin_h)
        assert r.json()["total"] == 1
        assert r.json()["list"][0]["content"] == "红色紧急预警"
        r = client.get("/api/warnings?keyword=已办结", headers=admin_h)
        assert r.json()["total"] == 1
        assert r.json()["list"][0]["level"] == "yellow"

    def test_list_ordering_red_first(self, client, admin_h):
        _reset_warnings()
        _mk_warning(level="yellow", content="黄")
        _mk_warning(level="red", content="红")
        r = client.get("/api/warnings", headers=admin_h)
        assert r.json()["list"][0]["level"] == "red"

    def test_level_and_status_names(self, client, admin_h):
        _reset_warnings()
        _mk_warning(level="red")
        row = client.get("/api/warnings", headers=admin_h).json()["list"][0]
        assert row["level_name"] == "紧急" and row["status_name"] == "待办"


class TestSummary:
    def test_summary_counts(self, client, admin_h):
        _reset_warnings()
        _mk_warning(level="red", status="pending")
        _mk_warning(level="yellow", status="handled")
        _mk_warning(level="green", status="pending")
        s = client.get("/api/warnings/summary", headers=admin_h).json()
        assert s["red"] == 1 and s["yellow"] == 1 and s["green"] == 1
        assert s["total"] == 3
        assert s["pending"] == 2 and s["handled"] == 1


class TestHandle:
    def test_handle(self, client, admin_h):
        wid = _mk_warning()
        r = client.post(f"/api/warnings/{wid}/handle", headers=admin_h, json={"remark": "已核实"})
        assert r.status_code == 200
        row = query_one("SELECT status,handle_user,remark FROM t_warning WHERE id=?", (wid,))
        assert row["status"] == "handled" and row["handle_user"] == "admin" and row["remark"] == "已核实"

    def test_postpone(self, client, manager_h):
        wid = _mk_warning()
        assert client.post(f"/api/warnings/{wid}/postpone", headers=manager_h, json={"remark": "延后"}).status_code == 200
        assert query_one("SELECT status FROM t_warning WHERE id=?", (wid,))["status"] == "postponed"

    def test_postpone_missing_404(self, client, admin_h):
        assert client.post("/api/warnings/999999/postpone", headers=admin_h, json={}).status_code == 404

    def test_handle_missing_404(self, client, admin_h):
        assert client.post("/api/warnings/999999/handle", headers=admin_h, json={}).status_code == 404

    def test_viewer_handle_forbidden(self, client, viewer_h):
        wid = _mk_warning()
        assert client.post(f"/api/warnings/{wid}/handle", headers=viewer_h, json={}).status_code == 403


class TestScanAndExport:
    def test_scan_runs(self, client, admin_h):
        r = client.post("/api/warnings/scan", headers=admin_h)
        assert r.status_code == 200
        assert "扫描完成" in r.json()["message"]

    def test_viewer_scan_forbidden(self, client, viewer_h):
        assert client.post("/api/warnings/scan", headers=viewer_h).status_code == 403

    def test_export_xlsx(self, client, admin_h):
        _mk_warning()
        r = client.get("/api/warnings/export", headers=admin_h)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers["content-type"]
