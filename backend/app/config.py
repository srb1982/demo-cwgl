import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "village.db")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

for _d in (DATA_DIR, UPLOAD_DIR, BACKUP_DIR):
    os.makedirs(_d, exist_ok=True)

JWT_SECRET = os.environ.get("CW_JWT_SECRET", "village-cw-20260731-secret")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 12

ROLE_ADMIN = "admin"      # 超级管理员
ROLE_MANAGER = "manager"  # 普通管理员
ROLE_VIEWER = "viewer"    # 只读用户

ROLE_NAMES = {
    ROLE_ADMIN: "超级管理员",
    ROLE_MANAGER: "普通管理员",
    ROLE_VIEWER: "只读用户",
}
