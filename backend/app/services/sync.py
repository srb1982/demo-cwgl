import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*", logger=False)


async def notify(event: str, data=None):
    """通过 WebSocket 向局域网所有客户端推送实时事件"""
    await sio.emit(event, data or {})


async def notify_data_changed(menu_code=None, module=None):
    """台账数据或元数据变更后触发全终端刷新"""
    await sio.emit("data_changed", {"menu_code": menu_code, "module": module, "time": __import__("datetime").datetime.now().isoformat()})


async def notify_warning():
    await sio.emit("warning_changed", {"time": __import__("datetime").datetime.now().isoformat()})
