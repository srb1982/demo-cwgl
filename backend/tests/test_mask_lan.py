import json
import uuid


def _mk():
    return "M" + uuid.uuid4().hex[:8].upper()


def _set_cfg(client, admin_h, key, value):
    old = client.get("/api/system/config", headers=admin_h).json()["config"].get(key)
    r = client.put("/api/system/config", headers=admin_h, json={"key": key, "value": value})
    assert r.status_code == 200, r.text
    return old


def _restore_cfg(client, admin_h, pairs):
    for key, value in pairs:
        if value is None:
            client.delete("/api/system/config", headers=admin_h, json={"key": key})
        else:
            _set_cfg(client, admin_h, key, value)


class TestMaskConfig:
    def test_default_list_masked(self, client, admin_h, manager_h):
        card = "110101199001011234"
        name = _mk()
        r = client.post("/api/ledger/villager", headers=manager_h,
                        json={"name": name, "id_card": card, "phone": "13800138000"})
        assert r.status_code == 200
        rows = client.get("/api/ledger/villager", headers=admin_h).json()["list"]
        row = next(x for x in rows if x["name"] == name)
        assert "*" in row["id_card"]
        assert "****" in row["phone"]

    def test_disable_mask_disables_list(self, client, admin_h, manager_h):
        name = _mk()
        client.post("/api/ledger/villager", headers=manager_h,
                    json={"name": name, "id_card": "110101199001011234"})
        old = _set_cfg(client, admin_h, "mask_enabled", "0")
        try:
            rows = client.get("/api/ledger/villager", headers=admin_h).json()["list"]
            row = next(x for x in rows if x["name"] == name)
            assert "*" not in row["id_card"]
        finally:
            _restore_cfg(client, admin_h, [("mask_enabled", old)])

    def test_custom_fields_only(self, client, admin_h, manager_h):
        name = _mk()
        client.post("/api/ledger/villager", headers=manager_h,
                    json={"name": name, "id_card": "110101199001011234", "phone": "13800138000"})
        old = _set_cfg(client, admin_h, "mask_fields", json.dumps(["phone"]))
        try:
            rows = client.get("/api/ledger/villager", headers=admin_h).json()["list"]
            row = next(x for x in rows if x["name"] == name)
            assert "*" not in row["id_card"]
            assert "****" in row["phone"]
        finally:
            _restore_cfg(client, admin_h, [("mask_fields", old)])

    def test_custom_rules(self, client, admin_h, manager_h):
        name = _mk()
        client.post("/api/ledger/villager", headers=manager_h,
                    json={"name": name, "phone": "13800138000"})
        old = _set_cfg(client, admin_h, "mask_rules",
                       json.dumps({"phone": {"head": 5, "tail": 3, "min_len": 11}}))
        try:
            rows = client.get("/api/ledger/villager", headers=admin_h).json()["list"]
            row = next(x for x in rows if x["name"] == name)
            assert row["phone"] == "13800***000"
        finally:
            _restore_cfg(client, admin_h, [("mask_rules", old)])

    def test_viewer_detail_masked_by_switch(self, client, admin_h, manager_h, viewer_h):
        name = _mk()
        r = client.post("/api/ledger/villager", headers=manager_h,
                        json={"name": name, "id_card": "110101199001011234"})
        iid = r.json()["id"]
        d = client.get(f"/api/ledger/villager/detail/{iid}", headers=viewer_h).json()["item"]
        assert "*" in d["id_card"]
        old = _set_cfg(client, admin_h, "mask_enabled", "0")
        try:
            d2 = client.get(f"/api/ledger/villager/detail/{iid}", headers=viewer_h).json()["item"]
            assert "*" not in d2["id_card"]
        finally:
            _restore_cfg(client, admin_h, [("mask_enabled", old)])


class TestLanMenu:
    def test_menus_registered(self, client, admin_h):
        menus = client.get("/api/menus", headers=admin_h).json()
        codes = [m["code"] for m in menus]
        assert "sys_lan" in codes
        assert "sys_mask" in codes

    def test_non_admin_hides_system_menus(self, client, manager_h):
        menus = client.get("/api/menus", headers=manager_h).json()
        codes = [m["code"] for m in menus]
        assert "sys_lan" not in codes
        assert "sys_mask" not in codes

    def test_lan_info_admin(self, client, admin_h):
        r = client.get("/api/system/lan", headers=admin_h)
        assert r.status_code == 200
        info = r.json()
        assert info["ips"]
        assert info["port"]
        assert isinstance(info["lan_enabled"], bool)

    def test_lan_info_viewer_forbidden(self, client, viewer_h):
        assert client.get("/api/system/lan", headers=viewer_h).status_code == 403

    def test_config_missing_key_404(self, client, admin_h):
        r = client.put("/api/system/config", headers=admin_h,
                       json={"key": "no_such_key_x", "value": "v"})
        assert r.status_code == 404
