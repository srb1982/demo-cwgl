# User Instruction Memory

This file records user instructions, preferences, and teachings for reference in future interactions.

## Format

### User Instruction Entry
User instruction entries should follow this format:

[User Instruction Summary]
- Date: [YYYY-MM-DD]
- Context: [Mentioned scenario or time]
- Instructions:
  - [Content of user teaching or instruction, described line by line]

### Project Knowledge Entry
Entries discovered by the Agent during task execution should follow this format:

[Project Knowledge Summary]
- Date: [YYYY-MM-DD]
- Context: Discovered by Agent while performing [specific task description]
- Category: [Operations & Deployment|Build Methods|Testing Methods|Troubleshooting & Debugging|Workflow & Collaboration|Environment Configuration]
- Instructions:
  - [Specific knowledge points, described line by line]

## Deduplication Strategy
- Before adding a new entry, check for similar or identical instructions.
- If a duplicate is found, skip the new entry or merge it with the existing one.
- When merging, update the context or date information.
- This helps avoid redundant entries and keeps the memory file tidy.

## Entries

[Project Knowledge Summary]
- Date: 2026-08-03
- Context: Discovered by Agent while performing 智慧乡村村务综合管理系统（React+FastAPI）开发、部署与验收
- Category: Build Methods | Operations & Deployment | Environment Configuration | Troubleshooting & Debugging
- Instructions:
  - 构建与部署：生产单端口一体化部署执行 `./build.sh`（构建前端并复制 dist 到 backend/static，由 FastAPI 托管 SPA 含路由回退），随后 `cd backend && python3 run.py` 监听 8000 端口即可局域网访问；开发模式 vite 5173 通过 proxy 转发 /api 与 /socket.io 到 8000。
  - 环境配置：沙箱为 Node v22.22.0 + Python 3.11.2；后端依赖见 backend/requirements.txt（pip 已装），前端依赖见 frontend/package.json（npm 已装）。前端无 lint 脚本，质量检查用 `cd frontend && npx tsc --noEmit`。
  - 数据与运维：数据库单文件 backend/data/village.db（WAL 模式）；上传附件在 backend/data/uploads/，加密备份在 backend/data/backups/；数据库/备份/static 已被 .gitignore 排除，不提交。
  - 演示数据：重置并重新生成干净演示数据执行 `cd backend && python3 seed_demo.py --reset`（清空 24 台账与预警表后按固定随机种子重新生成，含移风易俗红事/白事统计表）；重置后需手动触发 `POST /api/warnings/scan` 生成预警。
  - 三费字段约定：t_fee_collect 的 medical_status/pension_status/supplement_status 为金额存储（>0 已缴、0/空 未缴），三费面板(/api/fee)、大屏(/api/dashboard)、预警引擎(/api/warnings 扫描)均按金额判断，勿再用旧下拉值"已缴/未缴"。移风易俗已拆分为红事 t_custom_red 与白事 t_custom_white 两个台账，原 t_custom_rural 菜单隐藏（is_visible=0）保留数据。
  - 接口前缀：预警模块统一前缀为复数 `/api/warnings`（list/summary/scan/export/{id}/handle/{id}/postpone），三费为 `/api/fee`（years/groups/summary/unpaid/export），系统为 `/api/system`（backup/backups/restore/logs/config/archive-year/screen-config）。
  - 已知坑：导出/上传文件 Content-Disposition 必须使用 `filename*=UTF-8''{quote(fname)}`，否则中文文件名导致 500；元数据自定义字段物理列为 ext_N，事务化 ALTER TABLE 加列，删除走回收站软删除并保护内置字段；年度封存会对每张台账建 `t_*_{year}` 存档表并清空原表，封存前自动备份。

[Project Knowledge Summary]
- Date: 2026-08-07
- Context: Discovered by Agent while 为字段配置模块编写 pytest 集成测试
- Category: Testing Methods
- Instructions:
  - 后端集成测试：`cd backend && python3 -m pytest tests/ -v`；依赖 pytest 与 httpx（已全局安装）。测试通过 conftest.py 自动切换到临时隔离 SQLite 库并执行 seed 初始化，不触碰生产 data/village.db；已扩展为覆盖全部 11 个路由模块（字段/台账/菜单/用户/三费/预警/系统/档案/认证/概览）共 158 项断言。新增后端改动后跑一遍该套件可快速回归。
  - 后端测试套件已装 pytest-randomly 并通过随机顺序多种子验证（158 全过）；写测试须自包含、用独立唯一标识（uuid）造数，避免 session 共享库下的顺序依赖。
  - 后端新增依赖一律 `pip install --break-system-packages <pkg>`（系统 Python 无 venv）。

[Project Knowledge Summary]
- Date: 2026-08-08
- Context: Discovered by Agent while 为字段配置模块补充前端单元测试
- Category: Testing Methods
- Instructions:
  - 前端单元测试：`cd frontend && npm test`（vitest run，node 环境，vite.config.ts 的 test 段配置）。纯逻辑集中在 src/utils/ 下 8 个模块共 87 例（fieldValidation/fieldMeta/menuTree/fieldRender/fieldProps/ledgerPayload/fieldLibrary/tableFilters），页面组件复用这些函数后不再内联业务规则。新增前端改动后跑该套件 + `npx tsc --noEmit` + `npm run build` 回归。
