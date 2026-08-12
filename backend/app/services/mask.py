"""敏感字段脱敏规则配置

将原先硬编码的脱敏字段与保留位数改为可由「脱敏设置」菜单动态配置，
配置存储于 sys_config（mask_enabled / mask_fields / mask_rules）。
默认值与原硬编码行为保持一致。
"""

import json

from ..database import query_one

DEFAULT_FIELDS = [
    "id_card", "phone", "visa_no", "guardian_phone", "responsible_phone",
    "parent_phone", "emergency_phone", "helper_phone",
]
DEFAULT_RULES = {
    "id_card": {"head": 4, "tail": 4, "min_len": 15},
    "phone": {"head": 3, "tail": 4, "min_len": 11},
    "visa_no": {"head": 2, "tail": 2, "min_len": 5},
}
CONFIG_KEYS = ("mask_enabled", "mask_fields", "mask_rules")


def _load_json(s, default):
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


def get_mask_config():
    """读取脱敏配置，缺省项使用默认值"""
    cfg = {"enabled": True, "fields": list(DEFAULT_FIELDS), "rules": dict(DEFAULT_RULES)}
    try:
        row = query_one("SELECT config_value FROM sys_config WHERE config_key='mask_enabled'")
        if row:
            cfg["enabled"] = str(row["config_value"]) not in ("0", "false", "")
        row = query_one("SELECT config_value FROM sys_config WHERE config_key='mask_fields'")
        if row:
            fields = _load_json(row["config_value"], [])
            if isinstance(fields, list) and fields:
                cfg["fields"] = [f for f in fields if f]
        row = query_one("SELECT config_value FROM sys_config WHERE config_key='mask_rules'")
        if row:
            rules = _load_json(row["config_value"], {})
            if isinstance(rules, dict) and rules:
                cfg["rules"] = rules
    except Exception:
        pass
    return cfg


def _rule_for(field, rules):
    if field == "id_card":
        return rules.get("id_card")
    if field == "visa_no":
        return rules.get("visa_no")
    if "phone" in field:
        return rules.get("phone")
    return None


def mask_value_cfg(field, value, rules=None):
    """按配置规则脱敏单个值；rules 为 None 时使用默认规则（等价旧行为）"""
    if value is None:
        return None
    rules = rules or DEFAULT_RULES
    rule = _rule_for(field, rules)
    if not rule:
        return value
    s = str(value)
    min_len = int(rule.get("min_len", 0) or 0)
    if len(s) < min_len:
        return s
    head = int(rule.get("head", 0) or 0)
    tail = int(rule.get("tail", 0) or 0)
    if head + tail >= len(s):
        return s
    return s[:head] + "*" * (len(s) - head - tail) + s[-tail:]


def apply_mask_cfg(data, fields, cfg=None):
    """按配置对列表脱敏；未启用脱敏时原样返回"""
    if not data:
        return data
    cfg = cfg or get_mask_config()
    if not cfg.get("enabled"):
        return data
    mask_fields = set(cfg.get("fields") or [])
    rules = cfg.get("rules") or {}
    for item in data:
        for f in fields:
            if f in item and f in mask_fields:
                item[f] = mask_value_cfg(f, item.get(f), rules)
    return data
