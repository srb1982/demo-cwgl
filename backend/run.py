import uvicorn

from app.database import query_one


def boot_config():
    """从 sys_config 读取局域网访问配置决定监听 host 与端口；异常时回退默认值"""
    try:
        row = query_one("SELECT config_value FROM sys_config WHERE config_key='lan_enabled'")
        port_row = query_one("SELECT config_value FROM sys_config WHERE config_key='server_port'")
        lan_enabled = (row or {}).get("config_value", "1") not in ("0", "")
        port = int((port_row or {}).get("config_value", "8000") or 8000)
        host = "0.0.0.0" if lan_enabled else "127.0.0.1"
        return host, port
    except Exception:
        return "0.0.0.0", 8000


if __name__ == "__main__":
    host, port = boot_config()
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
