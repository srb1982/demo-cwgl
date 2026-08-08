import uuid

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
                       params={"label": "文化程度"})
        assert r.status_code == 200
        body = r.json()
        assert body["suggest"] == "wen_hua_cheng_du"
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
