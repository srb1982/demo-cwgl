import pytest

from app.database import execute


@pytest.fixture(autouse=True)
def _clean_config():
    execute("DELETE FROM sys_config WHERE config_key IN ('lan_enabled', 'server_port')")
    yield
    execute("DELETE FROM sys_config WHERE config_key IN ('lan_enabled', 'server_port')")


def test_boot_config_defaults_when_no_rows():
    from run import boot_config
    assert boot_config() == ("0.0.0.0", 8000)


def test_boot_config_lan_disabled_binds_loopback():
    from run import boot_config
    execute("INSERT INTO sys_config (config_key, config_value) VALUES ('lan_enabled', '0')")
    execute("INSERT INTO sys_config (config_key, config_value) VALUES ('server_port', '9000')")
    assert boot_config() == ("127.0.0.1", 9000)


def test_boot_config_lan_enabled_binds_all():
    from run import boot_config
    execute("INSERT INTO sys_config (config_key, config_value) VALUES ('lan_enabled', '1')")
    execute("INSERT INTO sys_config (config_key, config_value) VALUES ('server_port', '9001')")
    assert boot_config() == ("0.0.0.0", 9001)
