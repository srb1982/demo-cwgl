#!/bin/bash
# 智慧乡村村务综合管理系统 一键启动
cd "$(dirname "$0")/backend"
python3 -c "import fastapi, uvicorn, socketio, apscheduler" 2>/dev/null || pip install -r requirements.txt
echo "服务启动：http://localhost:8000"
python3 run.py
