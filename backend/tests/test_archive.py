import uuid

PDF = b"%PDF-1.4 fake content"


def _uniq(prefix):
    return f"{prefix}{uuid.uuid4().hex[:4]}"


def _upload(client, headers, filename="村民档案.pdf"):
    return client.post("/api/archive/upload", headers=headers,
                       files=[("files", (filename, PDF, "application/pdf"))])


class TestPermissions:
    def test_viewer_upload_forbidden(self, client, viewer_h):
        r = client.post("/api/archive/upload", headers=viewer_h,
                        files=[("files", ("a.pdf", PDF, "application/pdf"))])
        assert r.status_code == 403

    def test_viewer_relate_forbidden(self, client, viewer_h):
        assert client.post("/api/archive/1/relate", headers=viewer_h,
                           json={"menu_code": "villager", "villager_name": "x"}).status_code == 403

    def test_viewer_delete_forbidden(self, client, viewer_h):
        assert client.delete("/api/archive/1", headers=viewer_h).status_code == 403


class TestUpload:
    def test_upload_success(self, client, admin_h):
        r = _upload(client, admin_h)
        assert r.status_code == 200
        assert r.json()["items"]
        assert r.json()["items"][0]["file_name"] == "村民档案.pdf"

    def test_auto_classify_villager(self, client, admin_h):
        r = _upload(client, admin_h, filename="村民花名册.pdf")
        item = r.json()["items"][0]
        assert item["category"] == "villager"
        assert item["category_name"] == "村民信息"

    def test_auto_classify_fee(self, client, admin_h):
        r = _upload(client, admin_h, filename="三费收缴明细.pdf")
        assert r.json()["items"][0]["category"] == "fee_collect"

    def test_unsupported_ext_skipped(self, client, admin_h):
        r = client.post("/api/archive/upload", headers=admin_h,
                        files=[("files", ("病毒.exe", b"MZ", "application/octet-stream"))])
        assert r.status_code == 200
        assert r.json()["items"] == []


class TestList:
    def test_list_shape(self, client, admin_h):
        _upload(client, admin_h, filename="普通归档.pdf")
        r = client.get("/api/archive", headers=admin_h)
        assert r.status_code == 200
        assert r.json()["total"] >= 1
        assert all("category_name" in x and "url" in x for x in r.json()["list"])

    def test_list_category_filter(self, client, admin_h):
        _upload(client, admin_h, filename="低保申请材料.pdf")
        r = client.get("/api/archive?category=low_income", headers=admin_h)
        assert r.json()["total"] >= 1
        assert all(x["category"] == "low_income" for x in r.json()["list"])

    def test_list_keyword(self, client, admin_h):
        uniq = _uniq("走访")
        _upload(client, admin_h, filename=f"{uniq}记录.pdf")
        r = client.get(f"/api/archive?keyword={uniq}", headers=admin_h)
        assert r.json()["total"] >= 1

    def test_viewer_can_list(self, client, viewer_h):
        assert client.get("/api/archive", headers=viewer_h).status_code == 200


class TestRelateClassify:
    def test_relate(self, client, admin_h):
        fid = _upload(client, admin_h).json()["items"][0]["id"]
        r = client.post(f"/api/archive/{fid}/relate", headers=admin_h,
                        json={"menu_code": "villager", "villager_name": "张三"})
        assert r.status_code == 200
        row = client.get("/api/archive", headers=admin_h).json()["list"][0]
        assert row["villager_name"] == "张三" and row["menu_code"] == "villager"

    def test_classify(self, client, admin_h):
        fid = _upload(client, admin_h, filename="无关键字.pdf").json()["items"][0]["id"]
        r = client.post(f"/api/archive/{fid}/classify", headers=admin_h,
                        json={"menu_code": "party_member", "villager_name": ""})
        assert r.status_code == 200
        row = next(x for x in client.get("/api/archive", headers=admin_h).json()["list"] if x["id"] == fid)
        assert row["category"] == "party_member"

    def test_relate_missing_404(self, client, admin_h):
        r = client.post("/api/archive/999999/relate", headers=admin_h,
                        json={"menu_code": "villager", "villager_name": "x"})
        assert r.status_code == 404


class TestCategoriesAndDelete:
    def test_categories(self, client, admin_h):
        r = client.get("/api/archive/categories", headers=admin_h)
        assert r.status_code == 200
        assert any(c["code"] == "villager" for c in r.json())

    def test_delete(self, client, admin_h):
        fid = _upload(client, admin_h, filename="待删除.pdf").json()["items"][0]["id"]
        r = client.delete(f"/api/archive/{fid}", headers=admin_h)
        assert r.status_code == 200
        assert all(x["id"] != fid for x in client.get("/api/archive", headers=admin_h).json()["list"])

    def test_delete_missing_404(self, client, admin_h):
        assert client.delete("/api/archive/999999", headers=admin_h).status_code == 404
