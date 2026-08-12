from app.services import mask


class TestLoadJson:
    def test_empty_returns_default(self):
        assert mask._load_json("", ["x"]) == ["x"]
        assert mask._load_json(None, {"a": 1}) == {"a": 1}

    def test_invalid_json_returns_default(self):
        assert mask._load_json("not-json{", []) == []


class TestMaskValueCfg:
    def test_visa_no_rule(self):
        assert mask.mask_value_cfg("visa_no", "V123456", mask.DEFAULT_RULES) == "V1***56"

    def test_non_sensitive_field_returned(self):
        assert mask.mask_value_cfg("name", "张三", mask.DEFAULT_RULES) == "张三"

    def test_short_value_not_masked(self):
        assert mask.mask_value_cfg("phone", "138", mask.DEFAULT_RULES) == "138"

    def test_keep_cover_whole_length(self):
        rules = {"id_card": {"head": 4, "tail": 4, "min_len": 0}}
        assert mask.mask_value_cfg("id_card", "123", rules) == "123"

    def test_phone_with_default_rules(self):
        assert mask.mask_value_cfg("phone", "13800138000") == "138****8000"

    def test_none_value(self):
        assert mask.mask_value_cfg("id_card", None) is None


class TestApplyMaskCfg:
    def test_empty_data(self):
        assert mask.apply_mask_cfg([], ["id_card"]) == []

    def test_disabled_returns_data(self):
        data = [{"id_card": "110101199001011234"}]
        out = mask.apply_mask_cfg(data, ["id_card"], {"enabled": False, "fields": [], "rules": {}})
        assert out is data

    def test_masks_only_selected_fields(self):
        data = [{"id_card": "110101199001011234", "phone": "13800138000"}]
        out = mask.apply_mask_cfg(
            data, ["id_card", "phone"],
            {"enabled": True, "fields": ["phone"],
             "rules": {"phone": {"head": 3, "tail": 4, "min_len": 11}}})
        assert out[0]["id_card"] == "110101199001011234"
        assert out[0]["phone"] == "138****8000"
