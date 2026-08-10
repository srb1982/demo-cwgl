PDF = b"%PDF-1.4 content"


def _upload(client, headers):
    r = client.post("/api/archive/upload", headers=headers,
                    files=[("files", ("下载测试.pdf", PDF, "application/pdf"))])
    assert r.status_code == 200
    fid = r.json()["items"][0]["id"]
    rows = client.get("/api/archive", headers=headers).json()["list"]
    return next(x["url"] for x in rows if x["id"] == fid)


class TestFileAccess:
    def test_download_uploaded_file(self, client, admin_h):
        url = _upload(client, admin_h)
        r = client.get(url, headers=admin_h)
        assert r.status_code == 200
        assert r.content == PDF

    def test_missing_404(self, client, admin_h):
        assert client.get("/api/files/no_such.pdf", headers=admin_h).status_code == 404

    def test_path_traversal_403(self, client, admin_h):
        r = client.get("/api/files/%2e%2e/village.db", headers=admin_h)
        assert r.status_code == 403

    def test_unauth_401(self, client):
        assert client.get("/api/files/anything.pdf").status_code == 401

    def test_viewer_can_download(self, client, admin_h, viewer_h):
        url = _upload(client, admin_h)
        r = client.get(url, headers=viewer_h)
        assert r.status_code == 200
