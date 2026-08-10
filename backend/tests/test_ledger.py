import io
import uuid
from openpyxl import Workbook

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


def _xlsx(headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestLedgerFields:
    def test_fields_metadata(self, client, admin_h):
        r = client.get(f"/api/ledger/{MENU}/fields", headers=admin_h)
        assert r.status_code == 200
        body = r.json()
        assert body["menu"]["code"] == MENU
        assert body["fields"] and body["form_fields"] and body["list_fields"]
        assert all("physical_field" in f for f in body["fields"])

    def test_unknown_menu_fields_404(self, client, admin_h):
        assert client.get("/api/ledger/no_such/fields", headers=admin_h).status_code == 404


class TestAgeEdge:
    def test_age_autofill_15digit_idcard(self, client, admin_h):
        item_id = _create(client, admin_h, id_card="110101900101123")
        detail = client.get(f"/api/ledger/{MENU}/detail/{item_id}", headers=admin_h).json()["item"]
        assert detail.get("age") is not None
        assert 0 < detail["age"] <= 150

    def test_party_age_autofilled(self, client, admin_h):
        r = client.post("/api/ledger/party_member", headers=admin_h,
                        json={"name": "党员甲", "id_card": _mk_idcard(), "gender": "男", "join_date": "2000-07-01"})
        assert r.status_code == 200, r.text
        detail = client.get(f"/api/ledger/party_member/detail/{r.json()['id']}", headers=admin_h).json()["item"]
        assert detail.get("party_age") is not None
        assert detail["party_age"] >= 20

    def test_party_age_skips_when_provided(self, client, admin_h):
        r = client.post("/api/ledger/party_member", headers=admin_h,
                        json={"name": "党员乙", "id_card": _mk_idcard(), "gender": "男",
                              "join_date": "2000-07-01", "party_age": 10})
        detail = client.get(f"/api/ledger/party_member/detail/{r.json()['id']}", headers=admin_h).json()["item"]
        assert detail["party_age"] == 10

    def test_invalid_idcard_no_age(self, client, admin_h):
        item_id = _create(client, admin_h, id_card="12345")
        detail = client.get(f"/api/ledger/{MENU}/detail/{item_id}", headers=admin_h).json()["item"]
        assert detail.get("age") is None


class TestExportImport:
    def test_export_xlsx(self, client, admin_h):
        r = client.get(f"/api/ledger/{MENU}/export", headers=admin_h)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers["content-type"]

    def test_export_template_roundtrip(self, client, admin_h):
        r = client.post(f"/api/ledger/{MENU}/templates", headers=admin_h, json={"fields": ["name"]})
        assert r.status_code == 200
        tpls = client.get(f"/api/ledger/{MENU}/templates", headers=admin_h).json()
        assert tpls["templates"] == ["name"]
        r = client.get(f"/api/ledger/{MENU}/export?tpl=1", headers=admin_h)
        assert r.status_code == 200

    def test_import_success(self, client, admin_h):
        card = _mk_idcard()
        data = _xlsx(["姓名", "身份证号码"], [["导入甲", card]])
        r = client.post(f"/api/ledger/{MENU}/import", headers=admin_h,
                        files={"file": ("导入.xlsx", data,
                                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert r.status_code == 200
        assert "成功 1 条" in r.json()["message"]

    def test_import_duplicate_idcard_skipped(self, client, admin_h):
        card = _mk_idcard()
        _create(client, admin_h, id_card=card)
        data = _xlsx(["姓名", "身份证号码"], [["重复卡", card], ["正常乙", _mk_idcard()]])
        r = client.post(f"/api/ledger/{MENU}/import", headers=admin_h,
                        files={"file": ("导入.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert r.status_code == 200
        assert "重复跳过 1 条" in r.json()["message"]

    def test_import_bad_header_400(self, client, admin_h):
        data = _xlsx(["列甲", "列乙"], [["x", "y"]])
        r = client.post(f"/api/ledger/{MENU}/import", headers=admin_h,
                        files={"file": ("bad.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert r.status_code == 400

    def test_import_invalid_file_400(self, client, admin_h):
        r = client.post(f"/api/ledger/{MENU}/import", headers=admin_h,
                        files={"file": ("a.xlsx", b"not a real xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert r.status_code == 400

    def test_import_empty_rows_400(self, client, admin_h):
        data = _xlsx(["姓名", "身份证号码"], [])
        r = client.post(f"/api/ledger/{MENU}/import", headers=admin_h,
                        files={"file": ("empty.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert r.status_code == 400


class TestPrintAndUpload:
    def test_print_item(self, client, admin_h):
        item_id = _create(client, admin_h, name="打印甲")
        r = client.get(f"/api/ledger/{MENU}/print/{item_id}", headers=admin_h)
        assert r.status_code == 200
        body = r.json()
        assert body["menu_name"] == "村民信息台账"
        assert body["item"]["id"] == item_id
        assert body["fields"] and all(f["show_in_form"] for f in body["fields"])

    def test_print_missing_404(self, client, admin_h):
        assert client.get(f"/api/ledger/{MENU}/print/999999", headers=admin_h).status_code == 404

    def test_upload_image(self, client, admin_h):
        r = client.post("/api/ledger/upload-image", headers=admin_h,
                        files={"file": ("photo.png", b"\x89PNG\r\n\x1a\n", "image/png")})
        assert r.status_code == 200
        assert r.json()["url"].startswith("/api/files/")

    def test_upload_bad_ext_400(self, client, admin_h):
        r = client.post("/api/ledger/upload-image", headers=admin_h,
                        files={"file": ("a.sh", b"#!/bin/sh", "text/x-shellscript")})
        assert r.status_code == 400


class TestAgeBoundary:
    def test_calc_age_empty_input(self):
        from app.routers.ledger import _calc_age_from_idcard
        assert _calc_age_from_idcard(None) is None
        assert _calc_age_from_idcard("") is None

    def test_calc_party_age_edge(self):
        from app.routers.ledger import _calc_party_age
        assert _calc_party_age(None) is None
        assert _calc_party_age("") is None
        assert _calc_party_age("not-a-date") is None

    def test_no_idcard_no_age(self, client, admin_h):
        r = client.post(f"/api/ledger/{MENU}", headers=admin_h, json={"name": "无证甲"})
        assert r.status_code == 200, r.text
        detail = client.get(f"/api/ledger/{MENU}/detail/{r.json()['id']}", headers=admin_h).json()["item"]
        assert detail.get("age") is None

    def test_invalid_birth_date_no_age(self, client, admin_h):
        item_id = _create(client, admin_h, id_card="110101199013011234")
        detail = client.get(f"/api/ledger/{MENU}/detail/{item_id}", headers=admin_h).json()["item"]
        assert detail.get("age") is None

    def test_party_no_join_date(self, client, admin_h):
        r = client.post("/api/ledger/party_member", headers=admin_h,
                        json={"name": "党无日", "id_card": _mk_idcard(), "gender": "男"})
        detail = client.get(f"/api/ledger/party_member/detail/{r.json()['id']}", headers=admin_h).json()["item"]
        assert detail.get("party_age") is None

    def test_party_invalid_join_date(self, client, admin_h):
        r = client.post("/api/ledger/party_member", headers=admin_h,
                        json={"name": "党乱日", "id_card": _mk_idcard(), "gender": "男", "join_date": "abc"})
        detail = client.get(f"/api/ledger/party_member/detail/{r.json()['id']}", headers=admin_h).json()["item"]
        assert detail.get("party_age") is None


class TestCrudEdges:
    def test_update_missing_404(self, client, admin_h):
        r = client.put(f"/api/ledger/{MENU}/999999", headers=admin_h, json={"name": "不存在"})
        assert r.status_code == 404

    def test_templates_empty_without_config(self, client, admin_h):
        from app.database import execute
        execute("DELETE FROM sys_config WHERE config_key=?", (f"export_tpl_{MENU}",))
        r = client.get(f"/api/ledger/{MENU}/templates", headers=admin_h)
        assert r.status_code == 200
        assert r.json()["templates"] == []

    def test_export_with_empty_tpl_config(self, client, admin_h):
        client.post(f"/api/ledger/{MENU}/templates", headers=admin_h, json={"fields": []})
        r = client.get(f"/api/ledger/{MENU}/export?tpl=1", headers=admin_h)
        assert r.status_code == 200

    def test_import_skips_blank_middle_row(self, client, admin_h):
        data = _xlsx(["姓名", "身份证号码"],
                     [["前甲", _mk_idcard()], [None, None], ["后乙", _mk_idcard()]])
        r = client.post(f"/api/ledger/{MENU}/import", headers=admin_h,
                        files={"file": ("中空.xlsx", data,
                                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert r.status_code == 200
        assert "成功 2 条" in r.json()["message"]
