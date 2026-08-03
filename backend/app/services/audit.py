from datetime import datetime

from ..database import execute


def log_operation(user, action, module, detail="", ip=""):
    username = user.get("username") if user else "system"
    user_id = user.get("id") if user else None
    execute(
        "INSERT INTO sys_oper_log(user_id,username,action,module,detail,ip,create_time) VALUES(?,?,?,?,?,?,?)",
        (user_id, username, action, module, detail, ip, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
