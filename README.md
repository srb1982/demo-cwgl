# 智慧乡村村务综合管理系统

局域网离线部署的村务综合管理平台，采用 **React 18 + Ant Design 5 + FastAPI + SQLite + WebSocket** 技术栈，支持 24 套村务台账、零代码菜单/字段配置、文档智能归档、自动预警、三费收缴面板、离线数据大屏与备份恢复。

## 技术架构

| 层级 | 技术 |
|------|------|
| 表现层 | React 18 + TypeScript + Ant Design 5.x + Zustand + ECharts |
| 业务层 | Python FastAPI + Socket.IO + APScheduler |
| 数据层 | SQLite 单文件数据库（无需安装数据库服务） |
| 部署 | 单电脑集中部署，局域网浏览器访问，前端构建产物由后端一体化托管 |

## 目录结构

```
backend/               FastAPI 后端
  app/                 
    routers/           业务路由（认证/用户/菜单/字段/台账/归档/预警/三费/大屏/系统）
    services/          审计日志/实时同步/备份/预警引擎
    seed.py            数据库初始化：24套台账表 + 元数据 + 菜单 + 预置字段库
    seed_demo.py       演示数据生成脚本
  run.py               服务入口
frontend/              Vite + React 前端
  src/pages/           登录/台账/归档/预警/三费/大屏/系统管理
build.sh               一键构建前端并复制到 backend/static
```

## 快速启动（开发模式）

```bash
# 1. 启动后端
cd backend
pip install -r requirements.txt
python3 run.py                # http://0.0.0.0:8000

# 2. 启动前端
cd frontend
npm install
npm run dev                   # http://localhost:5173（代理 /api 与 /socket.io 到后端）
```

## 生产部署（单端口）

```bash
./build.sh                    # 构建前端并复制到 backend/static
cd backend && python3 run.py  # 单端口 http://主机IP:8000
```

局域网其他电脑浏览器访问 `http://主机内网IP:8000` 即可，无需安装客户端。

## 默认账号

- 超级管理员：`admin` / `admin123`

## 演示数据

```bash
cd backend && python3 seed_demo.py
```

生成村民、党员、残疾人、低保、三费收缴等 24 套台账演示数据（含移风易俗红事/白事统计表），随后在预警中心点击"立即扫描"生成预警。
