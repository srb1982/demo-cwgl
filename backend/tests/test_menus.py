import uuid


def _uniq(prefix):
    return f"{prefix}{uuid.uuid4().hex[:6]}"


class TestPermissions:
    def test_viewer_create_forbidden(self, client, viewer_h):
        r = client.post("/api/menus", headers=viewer_h, json={"code": _uniq("v"), "name": "x"})
        assert r.status_code == 403

    def test_manager_create_forbidden(self, client, manager_h):
        r = client.post("/api/menus", headers=manager_h, json={"code": _uniq("m"), "name": "x"})
        assert r.status_code == 403

    def test_viewer_update_forbidden(self, client, viewer_h):
        r = client.put("/api/menus/villager", headers=viewer_h, json={"name": "x"})
        assert r.status_code == 403

    def test_viewer_delete_forbidden(self, client, viewer_h):
        r = client.delete("/api/menus/villager", headers=viewer_h)
        assert r.status_code == 403


class TestList:
    def test_admin_sees_system(self, client, admin_h):
        r = client.get("/api/menus", headers=admin_h)
        assert r.status_code == 200
        assert any(m["code"] == "system" for m in r.json())

    def test_manager_hides_system_and_hidden(self, client, manager_h):
        r = client.get("/api/menus", headers=manager_h)
        assert r.status_code == 200
        rows = r.json()
        assert all(m["is_visible"] == 1 for m in rows)
        assert all(m["parent_code"] != "system" for m in rows)

    def test_tree_shape(self, client, admin_h):
        r = client.get("/api/menus/tree", headers=admin_h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert all("children" in m for m in r.json())


class TestCrud:
    def test_create_plain_menu(self, client, admin_h):
        code = _uniq("menu")
        r = client.post("/api/menus", headers=admin_h, json={"code": code, "name": "测试菜单"})
        assert r.status_code == 200, r.text
        assert any(m["code"] == code for m in client.get("/api/menus", headers=admin_h).json())

    def test_create_missing_fields_400(self, client, admin_h):
        assert client.post("/api/menus", headers=admin_h, json={"code": _uniq("c")}).status_code == 400
        assert client.post("/api/menus", headers=admin_h, json={"name": "无编码"}).status_code == 400

    def test_create_duplicate_code_400(self, client, admin_h):
        code = _uniq("dup")
        client.post("/api/menus", headers=admin_h, json={"code": code, "name": "一"})
        r = client.post("/api/menus", headers=admin_h, json={"code": code, "name": "二"})
        assert r.status_code == 400
        assert "已存在" in r.json()["detail"]

    def test_update_menu(self, client, admin_h):
        code = _uniq("upd")
        client.post("/api/menus", headers=admin_h, json={"code": code, "name": "原名"})
        r = client.put(f"/api/menus/{code}", headers=admin_h, json={"name": "新名", "sort_order": 9})
        assert r.status_code == 200
        row = next(m for m in client.get("/api/menus", headers=admin_h).json() if m["code"] == code)
        assert row["name"] == "新名" and row["sort_order"] == 9

    def test_update_missing_404(self, client, admin_h):
        r = client.put("/api/menus/no_such", headers=admin_h, json={"name": "x"})
        assert r.status_code == 404

    def test_delete_menu(self, client, admin_h):
        code = _uniq("del")
        client.post("/api/menus", headers=admin_h, json={"code": code, "name": "删除"})
        r = client.delete(f"/api/menus/{code}", headers=admin_h)
        assert r.status_code == 200
        assert all(m["code"] != code for m in client.get("/api/menus", headers=admin_h).json())

    def test_delete_missing_404(self, client, admin_h):
        r = client.delete("/api/menus/no_such", headers=admin_h)
        assert r.status_code == 404

    def test_delete_with_children_400(self, client, admin_h):
        parent = _uniq("parent")
        child = _uniq("child")
        client.post("/api/menus", headers=admin_h, json={"code": parent, "name": "父"})
        client.post("/api/menus", headers=admin_h, json={"code": child, "name": "子", "parent_code": parent})
        r = client.delete(f"/api/menus/{parent}", headers=admin_h)
        assert r.status_code == 400
        assert "子菜单" in r.json()["detail"]
        client.delete(f"/api/menus/{child}", headers=admin_h)


class TestLedgerMenu:
    def test_create_ledger_initializes_fields_and_table(self, client, admin_h):
        code = _uniq("ledger")
        table = f"t_{code}"
        r = client.post("/api/menus", headers=admin_h, json={"code": code, "name": "测试台账", "is_ledger": 1, "table_name": table})
        assert r.status_code == 200, r.text

        fs = client.get(f"/api/fields/{code}", headers=admin_h).json()
        assert isinstance(fs, list) and len(fs) >= 1
        assert any(f["physical_field"] == "name" for f in fs)

        item = client.post(f"/api/ledger/{code}", headers=admin_h, json={"name": "可录入"})
        assert item.status_code == 200, item.text

    def test_create_ledger_bad_table_name_400(self, client, admin_h):
        code = _uniq("bad")
        r = client.post("/api/menus", headers=admin_h, json={"code": code, "name": "坏表名", "is_ledger": 1, "table_name": "x; DROP TABLE"})
        assert r.status_code == 400

    def test_create_plain_menu_not_ledger(self, client, admin_h):
        code = _uniq("plain")
        client.post("/api/menus", headers=admin_h, json={"code": code, "name": "普通菜单", "is_ledger": 0})
        r = client.get(f"/api/ledger/{code}", headers=admin_h)
        assert r.status_code == 404
