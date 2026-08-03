@echo off
chcp 65001 >nul
title 智慧乡村村务综合管理系统
cd /d %~dp0backend

rem 首次运行自动安装后端依赖
python -c "import fastapi, uvicorn, socketio, apscheduler" >nul 2>&1
if errorlevel 1 (
    echo [初始化] 正在安装后端依赖，请稍候...
    pip install -r requirements.txt
)

echo 正在启动智慧乡村村务综合管理系统...
echo 访问地址：http://localhost:8000
start "" http://localhost:8000
python run.py
