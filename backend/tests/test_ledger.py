import uuid

MENU = "villager"


def _uniq(prefix):
    return f"{prefix}{uuid.uuid4().hex[:6]}"


def _mk_idcard():
    return "11010119900101" + uuid.uuid4().hex[:4].upper()


class TestPermissions:
    def test_viewer_create_forbidden(self, client, viewer_h):
        r = client.post(f"/api/ledger/{MENU}", headers=viewer_h, json={"name": _uniq("只读")})
        assert r.status_code == 403

    def test_viewer_update_forbidden(self, client, viewer_h, admin_h):
        item = _create(client, admin_h)
        r = client.put(f"/api/ledger/{MENU}/{item}", headers=viewer_h, json={"name": "x"})
        assert r.status_code == 403

    def test_viewer_delete_forbidden(self, client, viewer_h, admin_h):
        item = _create(client, admin_h)
        r = client.delete(f"/api/ledger/{MENU}/{item}", headers=viewer_h)
        assert r.status_code == 403

    def test_viewer_upload_forbidden(self, client, viewer_h):
        r = client.post("/api/ledger/upload-image", headers=viewer_h, files={"file": ("a.png", b"x", "image/png")})
        assert r.status_code == 403


class TestCrud:
    def test_create_and_read(self, client, admin_h):
        item_id = _create(client, admin_h, name="张三")
        r = client.get(f"/api/ledger/{MENU}/detail/{item_id}", headers=admin_h)
        assert r.status_code == 200
        assert r.json()["item"]["name"] == "张三"
        assert r.json()["item"]["create_time"]

    def test_update(self, client, admin_h):
        item_id = _create(client, admin_h, name="李四")
        r = client.put(f"/api/ledger/{MENU}/{item_id}", headers=admin_h, json={"name": "李四四"})
        assert r.status_code == 200
        detail = client.get(f"/api/ledger/{MENU}/detail/{item_id}", headers=admin_h).json()["item"]
        assert detail["name"] == "李四四"

    def test_delete(self, client, admin_h):
        item_id = _create(client, admin_h)
        r = client.delete(f"/api/ledger/{MENU}/{item_id}", headers=admin_h)
        assert r.status_code == 200
        assert client.get(f"/api/ledger/{MENU}/detail/{item_id}", headers=admin_h).status_code == 404

    def test_delete_missing_404(self, client, admin_h):
        r = client.delete(f"/api/ledger/{MENU}/999999", headers=admin_h)
        assert r.status_code == 404

    def test_detail_missing_404(self, client, admin_h):
        r = client.get(f"/api/ledger/{MENU}/detail/999999", headers=admin_h)
        assert r.status_code == 404

    def test_unknown_menu_404(self, client, admin_h):
        r = client.get("/api/ledger/no_such_menu", headers=admin_h)
        assert r.status_code == 404


class TestList:
    def test_keyword_search(self, client, admin_h):
        uniq = _uniq("搜索")
        _create(client, admin_h, name=uniq)
        r = client.get(f"/api/ledger/{MENU}?keyword={uniq}", headers=admin_h)
        assert r.status_code == 200
        names = [row["name"] for row in r.json()["list"]]
        assert uniq in names

    def test_filter(self, client, admin_h):
        group = _uniq("七组")
        _create(client, admin_h, name="过滤测", village_group=group)
        r = client.get(f"/api/ledger/{MENU}?filter_village_group={group}", headers=admin_h)
        assert r.json()["total"] >= 1
        assert all(row["village_group"] == group for row in r.json()["list"])

    def test_pagination(self, client, admin_h):
        r = client.get(f"/api/ledger/{MENU}?page=1&size=3", headers=admin_h)
        assert r.status_code == 200
        assert len(r.json()["list"]) <= 3
        assert r.json()["total"] >= 0

    def test_list_fields_shape(self, client, admin_h):
        r = client.get(f"/api/ledger/{MENU}", headers=admin_h)
        assert "list_fields" in r.json()
        assert all("id" in row for row in r.json()["list"])


class TestMasking:
    def test_viewer_detail_masked(self, client, viewer_h, admin_h):
        card = _mk_idcard()
        item_id = _create(client, admin_h, id_card=card)
        d = client.get(f"/api/ledger/{MENU}/detail/{item_id}", headers=viewer_h).json()["item"]
        assert d["id_card"] != card
        assert "*" in d["id_card"]

    def test_admin_detail_plaintext(self, client, admin_h):
        card = _mk_idcard()
        item_id = _create(client, admin_h, id_card=card)
        d = client.get(f"/api/ledger/{MENU}/detail/{item_id}", headers=admin_h).json()["item"]
        assert d["id_card"] == card


class TestDuplicates:
    def test_duplicate_idcard_reported(self, client, admin_h):
        card = _mk_idcard()
        _create(client, admin_h, id_card=card, name="重一")
        _create(client, admin_h, id_card=card, name="重二")
        r = client.get(f"/api/ledger/{MENU}/duplicates", headers=admin_h)
        assert r.status_code == 200
        dup = [x for x in r.json().get("id_card", []) if x["value"] == card]
        assert dup and dup[0]["count"] >= 2

    def test_no_duplicates_empty(self, client, admin_h):
        r = client.get(f"/api/ledger/{MENU}/duplicates", headers=admin_h)
        assert r.status_code == 200
        assert isinstance(r.json(), dict)


class TestAutoFill:
    def test_age_autofilled_from_idcard(self, client, admin_h):
        item_id = _create(client, admin_h, id_card="110101199001011234")
        detail = client.get(f"/api/ledger/{MENU}/detail/{item_id}", headers=admin_h).json()["item"]
        assert detail.get("age") is not None
        assert 0 < detail["age"] <= 150

    def test_age_autofill_skips_when_provided(self, client, admin_h):
        item_id = _create(client, admin_h, id_card="110101199001011234", age=30)
        detail = client.get(f"/api/ledger/{MENU}/detail/{item_id}", headers=admin_h).json()["item"]
        assert detail["age"] == 30


def _create(client, headers, **fields):
    payload = {"name": "默认姓名", "id_card": _mk_idcard()}
    payload.update({k: v for k, v in fields.items() if v is not None})
    r = client.post(f"/api/ledger/{MENU}", headers=headers, json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]
