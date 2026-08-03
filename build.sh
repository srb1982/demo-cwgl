#!/bin/bash
# 构建前端并复制到 backend/static，实现单端口一体化部署
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "[1/3] 安装前端依赖..."
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm install --no-fund --no-audit
fi

echo "[2/3] 构建前端..."
npm run build

echo "[3/3] 复制产物到 backend/static..."
mkdir -p "$ROOT/backend/static"
cp -r dist/* "$ROOT/backend/static/"

echo "构建完成。启动命令：cd backend && python3 run.py"
