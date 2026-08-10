from datetime import datetime

from app.database import execute, query_one, query_all


def _reset():
    execute("DELETE FROM t_warning")
    for t in ("t_disabled", "t_party_member", "t_elderly", "t_left_child", "t_village_public",
              "t_project", "t_public_job", "t_oversea", "t_village_move", "t_fee_collect"):
        execute(f"DELETE FROM {t}")


def _scan(client, headers):
    r = client.post("/api/warnings/scan", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["message"]


def _types():
    return {w["warning_type"] for w in query_all("SELECT DISTINCT warning_type FROM t_warning")}


def _mk(table, **cols):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    keys = list(cols.keys())
    qs = ",".join("?" for _ in cols)
    execute(f'INSERT INTO {table}({",".join(keys)},create_time) VALUES({qs},?)',
            list(cols.values()) + [now])


class TestRules:
    def test_disabled_cert_expire(self, client, admin_h):
        _reset()
        _mk("t_disabled", name="残一", expire_date="2020-01-01")
        _scan(client, admin_h)
        assert "cert_expire" in _types()

    def test_party_fee_and_positive(self, client, admin_h):
        _reset()
        _mk("t_party_member", name="党一", fee_status="欠缴", join_date="2020-01-01", positive_date="")
        _scan(client, admin_h)
        t = _types()
        assert "party_fee" in t and "party_positive" in t

    def test_elderly_subsidy_expire(self, client, admin_h):
        _reset()
        _mk("t_elderly", name="老一", expire_date="2020-01-01")
        _scan(client, admin_h)
        assert "subsidy_expire" in _types()

    def test_left_child_visit_overdue(self, client, admin_h):
        _reset()
        _mk("t_left_child", name="童一", last_visit_date="2020-01-01")
        _scan(client, admin_h)
        assert "visit_overdue" in _types()

    def test_public_expire(self, client, admin_h):
        _reset()
        _mk("t_village_public", public_title="公示一", expire_date="2020-01-01")
        _scan(client, admin_h)
        assert "public_expire" in _types()

    def test_project_deadline(self, client, admin_h):
        _reset()
        _mk("t_project", project_name="工程一", contract_end="2020-01-01")
        _scan(client, admin_h)
        assert "project_deadline" in _types()

    def test_job_renew(self, client, admin_h):
        _reset()
        _mk("t_public_job", person_name="岗一", contract_end="2020-01-01")
        _scan(client, admin_h)
        assert "job_renew" in _types()

    def test_oversea_visa_and_return(self, client, admin_h):
        _reset()
        _mk("t_oversea", name="境一", visa_expire_date="2020-01-01",
            return_date="2020-01-01", status="境外")
        _scan(client, admin_h)
        t = _types()
        assert "visa_expire" in t and "return_remind" in t

    def test_move_approve_timeout(self, client, admin_h):
        _reset()
        _mk("t_village_move", name="迁一", apply_date="2020-01-01", approve_status="待审批")
        _scan(client, admin_h)
        assert "move_approve" in _types()

    def test_fee_unpaid(self, client, admin_h):
        _reset()
        _mk("t_fee_collect", name="费一", fee_year="2020",
            medical_status=0, pension_status=0, supplement_status=0)
        _scan(client, admin_h)
        assert "fee_unpaid" in _types()


class TestLifecycle:
    def test_no_duplicate_on_rescan(self, client, admin_h):
        _reset()
        _mk("t_disabled", name="残二", expire_date="2020-01-01")
        _scan(client, admin_h)
        cnt1 = query_one("SELECT COUNT(*) c FROM t_warning WHERE warning_type='cert_expire'")["c"]
        _scan(client, admin_h)
        cnt2 = query_one("SELECT COUNT(*) c FROM t_warning WHERE warning_type='cert_expire'")["c"]
        assert cnt1 == 1 and cnt2 == 1

    def test_auto_resolve_when_condition_cleared(self, client, admin_h):
        _reset()
        _mk("t_disabled", name="残三", expire_date="2020-01-01")
        _scan(client, admin_h)
        wid = query_one("SELECT id FROM t_warning WHERE warning_type='cert_expire' AND content LIKE '%残三%'")["id"]
        execute("DELETE FROM t_disabled WHERE name='残三'")
        msg = _scan(client, admin_h)
        assert "自动办结" in msg
        assert query_one("SELECT status FROM t_warning WHERE id=?", (wid,))["status"] == "resolved"

    def test_scan_reports_counts(self, client, admin_h):
        _reset()
        _mk("t_disabled", name="残四", expire_date="2020-01-01")
        _mk("t_party_member", name="党二", fee_status="欠缴", join_date="2020-01-01", positive_date="")
        msg = _scan(client, admin_h)
        assert "新增预警 3 条" in msg
