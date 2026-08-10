import uuid

from app.database import execute
from app.routers.fields import _pinyin_code, _unique_code

MENU = "villager"


def _get_field(client, headers, menu=MENU, label=None):
    r = client.get(f"/api/fields/{menu}", headers=headers)
    assert r.status_code == 200, r.text
    fs = r.json()
    if isinstance(fs, dict):
        fs = fs.get("data", [])
    if label:
        return next((f for f in fs if f["display_label"] == label), None)
    return fs


def _uniq(prefix):
    return f"{prefix}{uuid.uuid4().hex[:6]}"


class TestPermissions:
    def test_viewer_browse_library(self, client, viewer_h):
        r = client.get("/api/fields/library/list", headers=viewer_h)
        assert r.status_code == 200

    def test_viewer_simple_create_allowed(self, client, viewer_h, admin_h):
        name = _uniq("查看者")
        r = client.post(f"/api/fields/{MENU}/simple", headers=viewer_h,
                        json={"display_label": name, "data_type": "text"})
        assert r.status_code == 200, r.text
        created = _get_field(client, viewer_h, label=name)
        assert created is not None
        client.delete(f"/api/fields/{created['id']}", headers=admin_h)

    def test_viewer_full_create_forbidden(self, client, viewer_h):
        r = client.post(f"/api/fields/{MENU}", headers=viewer_h,
                        json={"display_label": _uniq("禁止"), "data_type": "text"})
        assert r.status_code == 403

    def test_viewer_delete_forbidden(self, client, viewer_h):
        r = client.delete("/api/fields/1", headers=viewer_h)
        assert r.status_code == 403

    def test_viewer_visibility_toggle_forbidden(self, client, viewer_h):
        r = client.put("/api/fields/1", headers=viewer_h, json={"show_in_list": 0})
        assert r.status_code == 403

    def test_manager_no_category_admin(self, client, manager_h):
        r = client.post("/api/fields/library/categories", headers=manager_h,
                        json={"name": _uniq("mgr分类")})
        assert r.status_code == 403

    def test_manager_field_admin_allowed(self, client, manager_h):
        name = _uniq("管理员")
        r = client.post(f"/api/fields/{MENU}/simple", headers=manager_h,
                        json={"display_label": name, "data_type": "text"})
        assert r.status_code == 200, r.text
        created = _get_field(client, manager_h, label=name)
        assert created is not None
        r = client.delete(f"/api/fields/{created['id']}", headers=manager_h)
        assert r.status_code == 200


class TestRequiredProtection:
    def _required_field(self, client, headers):
        f = _get_field(client, headers, menu=MENU, label="身份证号码")
        assert f and f["is_required"] == 1
        return f

    def test_required_cannot_hide_in_list(self, client, admin_h):
        f = self._required_field(client, admin_h)
        r = client.put(f"/api/fields/{f['id']}", headers=admin_h, json={"show_in_list": 0})
        assert r.status_code == 400
        assert "必填" in r.json()["detail"]

    def test_required_cannot_hide_in_form(self, client, admin_h):
        f = self._required_field(client, admin_h)
        r = client.put(f"/api/fields/{f['id']}", headers=admin_h, json={"show_in_form": 0})
        assert r.status_code == 400

    def test_partial_update_keeps_other_fields(self, client, admin_h):
        f = self._required_field(client, admin_h)
        before = _get_field(client, admin_h, label="身份证号码")
        r = client.put(f"/api/fields/{f['id']}", headers=admin_h, json={"show_in_list": 1})
        assert r.status_code == 200
        after = _get_field(client, admin_h, label="身份证号码")
        assert after["is_required"] == before["is_required"] == 1
        assert after["show_in_form"] == before["show_in_form"] == 1


class TestSystemFieldLock:
    def test_system_field_type_locked(self, client, admin_h):
        f = _get_field(client, admin_h, label="身份证号码")
        assert f["is_system"] == 1
        r = client.put(f"/api/fields/{f['id']}", headers=admin_h,
                       json={"display_label": "身份证号码", "data_type": "number"})
        assert r.status_code == 400

    def test_system_field_cannot_delete(self, client, admin_h):
        f = _get_field(client, admin_h, label="身份证号码")
        r = client.delete(f"/api/fields/{f['id']}", headers=admin_h)
        assert r.status_code == 400


class TestDuplicateProtection:
    def test_duplicate_label_same_ledger(self, client, admin_h):
        name = _uniq("重名")
        r = client.post(f"/api/fields/{MENU}/simple", headers=admin_h,
                        json={"display_label": name, "data_type": "text"})
        assert r.status_code == 200, r.text
        r = client.post(f"/api/fields/{MENU}/simple", headers=admin_h,
                        json={"display_label": name, "data_type": "text"})
        assert r.status_code == 400
        assert "已添加到当前台账" in r.json()["detail"]

    def test_duplicate_label_other_ledger_allowed(self, client, admin_h):
        name = _uniq("跨台账")
        r = client.post(f"/api/fields/{MENU}/simple", headers=admin_h,
                        json={"display_label": name, "data_type": "text"})
        assert r.status_code == 200, r.text
        r = client.post("/api/fields/party_member/simple", headers=admin_h,
                        json={"display_label": name, "data_type": "text"})
        assert r.status_code == 200, r.text


class TestCodeGeneration:
    def test_code_suggest(self, client, admin_h):
        r = client.get(f"/api/fields/{MENU}/code-suggest", headers=admin_h,
                       params={"label": _uniq("程度")})
        assert r.status_code == 200
        body = r.json()
        assert body["suggest"]
        assert body["is_duplicate"] is False

    def test_code_suggest_duplicate_flag(self, client, admin_h):
        code = "dupsugg"
        r = client.post(f"/api/fields/{MENU}/simple", headers=admin_h,
                        json={"display_label": _uniq("重复建议"), "data_type": "text", "code": code})
        assert r.status_code == 200, r.text
        r = client.get(f"/api/fields/{MENU}/code-suggest", headers=admin_h,
                       params={"label": code})
        assert r.status_code == 200
        body = r.json()
        assert body["is_duplicate"] is True
        assert body["suggest"] == f"{code}_2"

    def test_library_excludes_added(self, client, admin_h):
        fs = _get_field(client, admin_h)
        used = {f["physical_field"] for f in fs}
        r = client.get("/api/fields/library/list", headers=admin_h, params={"menu_code": MENU})
        assert r.status_code == 200
        lib_names = {x["name"] for x in r.json()}
        assert lib_names.isdisjoint(used)

    def test_manual_code_duplicate(self, client, admin_h):
        r = client.post(f"/api/fields/{MENU}/simple", headers=admin_h,
                        json={"display_label": _uniq("编码"), "data_type": "text", "code": "name"})
        assert r.status_code == 400
        assert "编码已存在" in r.json()["detail"]

    def test_invalid_code_format(self, client, admin_h):
        r = client.post(f"/api/fields/{MENU}/simple", headers=admin_h,
                        json={"display_label": _uniq("非法编码"), "data_type": "text", "code": "1bad code"})
        assert r.status_code == 400


class TestCategoryManagement:
    def test_category_crud(self, client, admin_h):
        name = _uniq("测试分类")
        r = client.post("/api/fields/library/categories", headers=admin_h, json={"name": name})
        assert r.status_code == 200, r.text
        new = _uniq("改名")
        r = client.put(f"/api/fields/library/categories/{name}", headers=admin_h, json={"name": new})
        assert r.status_code == 200, r.text
        r = client.delete(f"/api/fields/library/categories/{new}", headers=admin_h)
        assert r.status_code == 200

    def test_category_duplicate_name(self, client, admin_h):
        r = client.post("/api/fields/library/categories", headers=admin_h, json={"name": "基础信息"})
        assert r.status_code == 400

    def test_category_delete_in_use_rejected(self, client, admin_h):
        r = client.delete("/api/fields/library/categories/基础信息", headers=admin_h)
        assert r.status_code == 400
        assert "还有" in r.json()["detail"]

    def test_category_empty_name(self, client, admin_h):
        r = client.post("/api/fields/library/categories", headers=admin_h, json={"name": ""})
        assert r.status_code == 400


class TestSimpleCreateProps:
    def test_simple_create_with_default_value_and_regex(self, client, admin_h):
        name = _uniq("车牌号")
        r = client.post(f"/api/fields/{MENU}/simple", headers=admin_h,
                        json={"display_label": name, "data_type": "text",
                              "props": {"default_value": "川A", "col_span": 2,
                                        "regex": "^[\\u4e00-\\u9fa5][A-Z]",
                                        "regex_message": "格式不正确"}})
        assert r.status_code == 200, r.text
        created = _get_field(client, admin_h, label=name)
        assert created is not None
        props = created.get("props") or {}
        assert props.get("default_value") == "川A"
        assert props.get("col_span") == 2
        assert props.get("regex") is not None

    def test_simple_create_adds_physical_column(self, client, admin_h):
        import sqlite3
        from app import config
        name = _uniq("物理列")
        r = client.post(f"/api/fields/{MENU}/simple", headers=admin_h,
                        json={"display_label": name, "data_type": "select", "options": ["A", "B"]})
        assert r.status_code == 200, r.text
        f = _get_field(client, admin_h, label=name)
        table = next(m["table_name"] for m in client.get("/api/menus", headers=admin_h).json()
                     if m["code"] == MENU)
        conn = sqlite3.connect(config.DB_PATH)
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        conn.close()
        assert f["physical_field"] in cols

    def test_custom_field_type_change(self, client, admin_h):
        name = _uniq("类型")
        r = client.post(f"/api/fields/{MENU}/simple", headers=admin_h,
                        json={"display_label": name, "data_type": "text"})
        assert r.status_code == 200, r.text
        created = _get_field(client, admin_h, label=name)
        r = client.put(f"/api/fields/{created['id']}", headers=admin_h,
                       json={"display_label": name, "data_type": "number"})
        assert r.status_code == 200, r.text
        after = _get_field(client, admin_h, label=name)
        assert after["data_type"] == "number"

    def test_required_label(self, client, admin_h):
        r = client.post(f"/api/fields/{MENU}/simple", headers=admin_h,
                        json={"display_label": "", "data_type": "text"})
        assert r.status_code == 400

    def test_invalid_type(self, client, admin_h):
        r = client.post(f"/api/fields/{MENU}/simple", headers=admin_h,
                        json={"display_label": _uniq("类型"), "data_type": "unknown"})
        assert r.status_code == 400


class TestNewLedgerAutoInit:
    def test_create_ledger_initializes_fields(self, client, admin_h):
        code = _uniq("tl")
        r = client.post("/api/menus", headers=admin_h,
                        json={"code": code, "name": "自动初始化台账", "is_ledger": 1,
                              "is_visible": 1, "table_name": f"t_{code}"})
        assert r.status_code == 200, r.text
        fs = _get_field(client, admin_h, menu=code)
        assert len(fs) >= 1
        assert all(f["is_system"] == 1 for f in fs)
        assert all(f["show_in_list"] == 1 and f["show_in_form"] == 1 for f in fs)
        client.delete(f"/api/menus/{code}", headers=admin_h)

    def test_create_ledger_creates_table_and_columns(self, client, admin_h):
        import sqlite3
        from app import config
        code = _uniq("tl2")
        r = client.post("/api/menus", headers=admin_h,
                        json={"code": code, "name": "建表验证台账", "is_ledger": 1,
                              "is_visible": 1, "table_name": f"t_{code}"})
        assert r.status_code == 200, r.text
        conn = sqlite3.connect(config.DB_PATH)
        tabs = {x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert f"t_{code}" in tabs, "台账表未创建"
        cols = {x[1] for x in conn.execute(f"PRAGMA table_info(t_{code})")}
        conn.close()
        fs = _get_field(client, admin_h, menu=code)
        assert all(f["physical_field"] in cols for f in fs), "初始化字段物理列缺失"
        payload = {f["physical_field"]: f"值{f['physical_field']}" for f in fs[:2]}
        r2 = client.post(f"/api/ledger/{code}", headers=admin_h, json=payload)
        assert r2.status_code == 200, f"录入失败: {r2.text}"
        client.delete(f"/api/menus/{code}", headers=admin_h)

    def test_non_ledger_no_init(self, client, admin_h):
        code = _uniq("nm")
        r = client.post("/api/menus", headers=admin_h,
                        json={"code": code, "name": "普通菜单", "is_ledger": 0,
                              "is_visible": 1})
        assert r.status_code == 200, r.text
        r = client.get(f"/api/fields/{code}", headers=admin_h)
        assert r.status_code in (400, 404)


class TestConcurrentConflict:
    def test_stale_update_time_conflict(self, client, admin_h):
        f = _get_field(client, admin_h, label="性别")
        assert f.get("update_time")
        r = client.put(f"/api/fields/{f['id']}", headers=admin_h,
                       json={"display_label": "性别", "update_time": "2000-01-01 00:00:00"})
        assert r.status_code == 409
        assert "已被他人修改" in r.json()["detail"]

    def test_current_update_time_accepted(self, client, admin_h):
        f = _get_field(client, admin_h, label="性别")
        r = client.put(f"/api/fields/{f['id']}", headers=admin_h,
                       json={"display_label": "性别", "update_time": f["update_time"]})
        assert r.status_code == 200, r.text

    def test_list_returns_update_time(self, client, admin_h):
        fs = _get_field(client, admin_h)
        assert all("update_time" in f for f in fs)


class TestRecycleAndSort:
    def test_delete_then_restore(self, client, admin_h):
        name = _uniq("回收")
        r = client.post(f"/api/fields/{MENU}/simple", headers=admin_h,
                        json={"display_label": name, "data_type": "text"})
        created = _get_field(client, admin_h, label=name)
        fid = created["id"]
        r = client.delete(f"/api/fields/{fid}", headers=admin_h)
        assert r.status_code == 200
        r = client.get(f"/api/fields/{MENU}/recycle", headers=admin_h)
        assert any(f["id"] == fid for f in r.json())
        r = client.post(f"/api/fields/{fid}/restore", headers=admin_h)
        assert r.status_code == 200
        assert _get_field(client, admin_h, label=name) is not None

    def test_sort_persist(self, client, admin_h):
        fs = _get_field(client, admin_h)
        ids = [f["id"] for f in fs]
        reversed_ids = list(reversed(ids))
        r = client.post(f"/api/fields/{MENU}/sort", headers=admin_h, json={"order": reversed_ids})
        assert r.status_code == 200, r.text
        after = _get_field(client, admin_h)
        assert [f["id"] for f in after] == reversed_ids
        r = client.post(f"/api/fields/{MENU}/sort", headers=admin_h, json={"order": ids})
        assert r.status_code == 200


class TestBulkSave:
    def test_bulk_update_existing(self, client, admin_h):
        f = _get_field(client, admin_h)[0]
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h, json={"fields": [
            {"id": f["id"], "display_label": f["display_label"], "is_required": f["is_required"],
             "show_in_form": f["show_in_form"], "show_in_list": f["show_in_list"], "props": {"tips": "批量保存测试"}},
        ]})
        assert r.status_code == 200, r.text
        assert r.json()["updated"] == 1
        after = _get_field(client, admin_h, label=f["display_label"])
        assert after["props"]["tips"] == "批量保存测试"

    def test_bulk_create_new(self, client, admin_h):
        name = _uniq("批量新增")
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h, json={"fields": [
            {"display_label": name, "data_type": "text", "show_in_list": 1, "show_in_form": 1, "is_required": 0},
        ]})
        assert r.status_code == 200, r.text
        assert r.json()["created"] == 1
        assert _get_field(client, admin_h, label=name) is not None

    def test_bulk_create_adds_physical_column(self, client, admin_h):
        import sqlite3
        from app import config
        name = _uniq("建列")
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h, json={"fields": [
            {"display_label": name, "data_type": "number", "show_in_list": 1, "show_in_form": 1, "is_required": 0},
        ]})
        assert r.status_code == 200, r.text
        f = _get_field(client, admin_h, label=name)
        table = None
        menus = client.get("/api/menus", headers=admin_h).json()
        for m in menus:
            if m["code"] == MENU:
                table = m["table_name"]
        assert table
        conn = sqlite3.connect(config.DB_PATH)
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        conn.close()
        assert f["physical_field"] in cols

    def test_bulk_required_cannot_hide(self, client, admin_h):
        f = _get_field(client, admin_h, label="身份证号码")
        assert f["is_required"] == 1
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h, json={"fields": [
            {"id": f["id"], "is_required": 1, "show_in_form": 0},
        ]})
        assert r.status_code == 400
        assert "必填" in r.json()["detail"]

    def test_bulk_system_type_locked(self, client, admin_h):
        f = _get_field(client, admin_h, label="身份证号码")
        assert f["is_system"] == 1
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h, json={"fields": [
            {"id": f["id"], "data_type": "number"},
        ]})
        assert r.status_code == 400
        assert "类型锁定" in r.json()["detail"]

    def test_bulk_rollback_on_failure(self, client, admin_h):
        f = _get_field(client, admin_h)[0]
        before_label = f["display_label"]
        name = _uniq("回滚字段")
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h, json={"fields": [
            {"id": f["id"], "display_label": "不应生效"},
            {"display_label": name, "data_type": "text", "is_required": 1, "show_in_form": 0},
        ]})
        assert r.status_code == 400
        assert _get_field(client, admin_h, label=before_label) is not None
        assert _get_field(client, admin_h, label="不应生效") is None
        assert _get_field(client, admin_h, label=name) is None


class TestCreateFieldEndpoint:
    def test_create_field_success(self, client, admin_h):
        label = _uniq("完整")
        r = client.post(f"/api/fields/{MENU}", headers=admin_h,
                        json={"display_label": label, "data_type": "text",
                              "show_in_list": 1, "show_in_form": 1, "is_required": 0})
        assert r.status_code == 200
        assert r.json()["physical_field"].startswith("ext_")
        assert _get_field(client, admin_h, label=label) is not None

    def test_create_field_missing_label_400(self, client, admin_h):
        assert client.post(f"/api/fields/{MENU}", headers=admin_h,
                           json={"data_type": "text"}).status_code == 400

    def test_create_field_invalid_type_400(self, client, admin_h):
        r = client.post(f"/api/fields/{MENU}", headers=admin_h,
                        json={"display_label": _uniq("类型"), "data_type": "blob"})
        assert r.status_code == 400

    def test_create_field_duplicate_label_400(self, client, admin_h):
        label = _uniq("重复")
        client.post(f"/api/fields/{MENU}", headers=admin_h,
                    json={"display_label": label, "data_type": "text"})
        r = client.post(f"/api/fields/{MENU}", headers=admin_h,
                        json={"display_label": label, "data_type": "text"})
        assert r.status_code == 400

    def test_create_field_non_ledger_404(self, client, admin_h):
        r = client.post("/api/fields/not_a_ledger", headers=admin_h,
                        json={"display_label": "x", "data_type": "text"})
        assert r.status_code == 404


class TestUpdateFieldEdges:
    def test_update_missing_404(self, client, admin_h):
        assert client.put("/api/fields/999999", headers=admin_h,
                          json={"display_label": "x"}).status_code == 404

    def test_update_custom_invalid_type_400(self, client, admin_h):
        label = _uniq("改型")
        client.post(f"/api/fields/{MENU}", headers=admin_h,
                    json={"display_label": label, "data_type": "text"})
        fid = _get_field(client, admin_h, label=label)["id"]
        r = client.put(f"/api/fields/{fid}", headers=admin_h, json={"data_type": "blob"})
        assert r.status_code == 400

    def test_update_props_non_dict_422(self, client, admin_h):
        label = _uniq("规检")
        client.post(f"/api/fields/{MENU}", headers=admin_h,
                    json={"display_label": label, "data_type": "text"})
        fid = _get_field(client, admin_h, label=label)["id"]
        assert client.put(f"/api/fields/{fid}", headers=admin_h,
                          json={"props": "not-a-dict"}).status_code == 422

    def test_delete_missing_404(self, client, admin_h):
        assert client.delete("/api/fields/999999", headers=admin_h).status_code == 404

    def test_delete_protected_field_400(self, client, admin_h):
        label = _uniq("保护")
        client.post("/api/fields/elderly", headers=admin_h,
                    json={"display_label": label, "data_type": "text"})
        fid = _get_field(client, admin_h, menu="elderly", label=label)["id"]
        execute("UPDATE sys_field_config SET physical_field='expire_date',is_system=0 WHERE id=?", (fid,))
        r = client.delete(f"/api/fields/{fid}", headers=admin_h)
        assert r.status_code == 400
        assert "预警规则" in r.json()["detail"]

    def test_restore_missing_404(self, client, admin_h):
        assert client.post("/api/fields/999999/restore", headers=admin_h).status_code == 404


class TestBulkEdges:
    def test_bulk_update_missing_404(self, client, admin_h):
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h,
                       json={"fields": [{"id": 999999, "display_label": "x"}]})
        assert r.status_code == 404

    def test_bulk_update_custom_invalid_type_400(self, client, admin_h):
        label = _uniq("bulk改")
        client.post(f"/api/fields/{MENU}", headers=admin_h,
                    json={"display_label": label, "data_type": "text"})
        fid = _get_field(client, admin_h, label=label)["id"]
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h,
                       json={"fields": [{"id": fid, "data_type": "blob"}]})
        assert r.status_code == 400

    def test_bulk_required_hide_list_400(self, client, admin_h):
        fid = _get_field(client, admin_h, label="姓名")["id"]
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h,
                       json={"fields": [{"id": fid, "is_required": 1, "show_in_list": 0}]})
        assert r.status_code == 400

    def test_bulk_create_missing_label_400(self, client, admin_h):
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h,
                       json={"fields": [{"data_type": "text"}]})
        assert r.status_code == 400

    def test_bulk_create_invalid_type_400(self, client, admin_h):
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h,
                       json={"fields": [{"display_label": _uniq("t"), "data_type": "blob"}]})
        assert r.status_code == 400

    def test_bulk_create_duplicate_label_400(self, client, admin_h):
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h,
                       json={"fields": [{"display_label": "姓名", "data_type": "text"}]})
        assert r.status_code == 400
        assert "已添加到当前台账" in r.json()["detail"]

    def test_bulk_create_pinyin_conflict_deep(self, client, admin_h):
        r1 = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h,
                        json={"fields": [{"display_label": "文化成度", "data_type": "text"}]})
        assert r1.status_code == 200
        r2 = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h,
                        json={"fields": [{"display_label": "文化成渡", "data_type": "text"}]})
        assert r2.status_code == 200
        r3 = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h,
                        json={"fields": [{"display_label": "文华成度", "data_type": "text"}]})
        assert r3.status_code == 200
        codes = {f["physical_field"] for f in _get_field(client, admin_h)}
        assert "wen_hua_cheng_du_3" in codes

    def test_bulk_create_no_pinyin_uses_ext(self, client, admin_h):
        r = client.put(f"/api/fields/{MENU}/bulk", headers=admin_h,
                       json={"fields": [{"display_label": "！！！", "data_type": "text"}]})
        assert r.status_code == 200
        got = [f["physical_field"] for f in _get_field(client, admin_h) if f["display_label"] == "！！！"]
        assert got and got[0].startswith("ext_")


class TestCodeSuggestEdges:
    def test_code_suggest_no_pinyin(self, client, admin_h):
        r = client.get(f"/api/fields/{MENU}/code-suggest?label=！！！", headers=admin_h)
        body = r.json()
        assert body["suggest"] == ""
        assert body["note"] != ""


class TestLibraryFilters:
    def test_library_categories_list(self, client, admin_h):
        cats = client.get("/api/fields/library/categories", headers=admin_h).json()
        assert isinstance(cats, list) and cats

    def test_library_category_filter(self, client, admin_h):
        cat = client.get("/api/fields/library/categories", headers=admin_h).json()[0]
        rows = client.get(f"/api/fields/library/list?category={cat}", headers=admin_h).json()
        assert all(f["category"] == cat for f in rows)

    def test_library_keyword_filter(self, client, admin_h):
        rows = client.get("/api/fields/library/list?keyword=姓名", headers=admin_h).json()
        assert rows
        assert all("姓名" in f["label"] or "姓名" in f["name"] for f in rows)

    def test_library_type_filter(self, client, admin_h):
        rows = client.get("/api/fields/library/list?field_type=text", headers=admin_h).json()
        assert all(f["data_type"] == "text" for f in rows)


class TestCategoryEdges:
    def test_create_category_too_long_400(self, client, admin_h):
        r = client.post("/api/fields/library/categories", headers=admin_h, json={"name": "长" * 21})
        assert r.status_code == 400

    def test_rename_category_invalid_400(self, client, admin_h):
        assert client.put("/api/fields/library/categories/x", headers=admin_h,
                          json={"name": ""}).status_code == 400

    def test_rename_category_missing_404(self, client, admin_h):
        assert client.put("/api/fields/library/categories/no_such_cat", headers=admin_h,
                          json={"name": "新名"}).status_code == 404

    def test_rename_category_duplicate_400(self, client, admin_h):
        cats = client.get("/api/fields/library/categories", headers=admin_h).json()
        r = client.put(f"/api/fields/library/categories/{cats[1]}", headers=admin_h,
                       json={"name": cats[0]})
        assert r.status_code == 400

    def test_rename_category_success(self, client, admin_h):
        name = _uniq("待改")
        client.post("/api/fields/library/categories", headers=admin_h, json={"name": name})
        new = _uniq("新类")
        r = client.put(f"/api/fields/library/categories/{name}", headers=admin_h, json={"name": new})
        assert r.status_code == 200
        cats = client.get("/api/fields/library/categories", headers=admin_h).json()
        assert new in cats and name not in cats

    def test_delete_category_missing_404(self, client, admin_h):
        assert client.delete("/api/fields/library/categories/no_such", headers=admin_h).status_code == 404


class TestFieldHelpers:
    def test_pinyin_code_no_valid_chars(self):
        assert _pinyin_code("！！！") is None

    def test_pinyin_code_truncates(self):
        code = _pinyin_code("很" * 30)
        assert code is not None and len(code) <= 50

    def test_pinyin_code_without_pypinyin(self, monkeypatch):
        monkeypatch.setattr("app.routers.fields._HAS_PINYIN", False)
        assert _pinyin_code("姓名") is None

    def test_unique_code_empty(self):
        assert _unique_code(MENU, "") is None

    def test_unique_code_conflict_appends(self, client, admin_h):
        base = _uniq("base").lower()[:12]
        execute("INSERT INTO sys_field_config(menu_code,physical_field,display_label,data_type,form_component,is_system,show_in_list,show_in_form,is_required,sort_order,is_deleted,create_time,update_time)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (MENU, base, "占位", "text", "input", 0, 1, 1, 0, 99, 0, "2026-01-01 00:00:00", "2026-01-01 00:00:00"))
        assert _unique_code(MENU, base) == f"{base}_2"
        assert _unique_code(MENU, f"{base}_zzz") == f"{base}_zzz"

    def test_fmt_bad_props_json(self, client, admin_h):
        fid = _get_field(client, admin_h, label="姓名")["id"]
        execute("UPDATE sys_field_config SET props_json='{bad json' WHERE id=?", (fid,))
        f = next(x for x in client.get(f"/api/fields/{MENU}", headers=admin_h).json() if x["id"] == fid)
        assert f["props"] == {}
