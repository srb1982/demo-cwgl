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
  - 后端集成测试：`cd backend && python3 -m pytest tests/ -v`；依赖 pytest 与 httpx（已全局安装）。测试通过 conftest.py 自动切换到临时隔离 SQLite 库并执行 seed 初始化，不触碰生产 data/village.db；已扩展为覆盖全部路由模块（字段/台账/菜单/用户/三费/预警/系统/档案/认证/概览/备份/定时任务/家庭联动）共 316 项断言，总覆盖率 97%（coverage run --source=app -m pytest tests/）。新增后端改动后跑一遍该套件可快速回归。
  - 家庭联动模块（app/services/family.py，仅作用于 villager 台账）：家庭键=household_no，户主=householder=='是'，人数=population（联动自动重算覆盖手填，含Excel导入后统一重算），单人户=户号下1人。多人户户主变更户号/降级/删除会被 400 阻断，须先交接（接口 POST /ledger/villager/transfer-householder）；单人户户主可自由删除/迁出。已知规则：单人户户主并入已有户主的户时自动降级为普通成员（保留目标户主）。前端 LedgerPage 有户主 Tag、删除引导交接弹窗、编辑表单红色提示。其余 30+ 台账不受影响。
  - 后端测试套件已装 pytest-randomly 并通过随机顺序多种子验证（289 全过，连续多次无偶发）；写测试须自包含、用独立唯一标识（uuid）造数，避免 session 共享库下的顺序依赖（曾踩坑：rename 分类破坏 seed 分类、code-suggest 固定 label 与新增字段冲突、_pick_year 取库中最大年份受 uuid 字符串排序影响——此类"取最新/最大"场景改用固定哨兵值如 Z999）。
  - 覆盖率驱动补测：先用 coverage 定位盲区再写测试。已知不测的高风险路径：restore_backup 真实恢复（替换 DB 文件）、年度封存成功路径（清空全部台账表）、PaddleOCR 成功分支（未安装属死代码）、users.py 删除当前登录账号分支（admin 删自己先撞"禁删内置管理员"，不可达）。
  - 后端新增依赖一律 `pip install --break-system-packages <pkg>`（系统 Python 无 venv）。

[Project Knowledge Summary]
- Date: 2026-08-08
- Context: Discovered by Agent while 为字段配置模块补充前端单元测试
- Category: Testing Methods
- Instructions:
  - 前端单元测试：`cd frontend && npm test`（vitest run，node 环境，vite.config.ts 的 test 段配置）。纯逻辑集中在 src/utils/ 下 8 个模块共 96 例（fieldValidation/fieldMeta/menuTree/fieldRender/fieldProps/ledgerPayload/fieldLibrary/tableFilters），页面组件复用这些函数后不再内联业务规则。前端覆盖率：`npx vitest run --coverage`（需 @vitest/coverage-v8@1.6.1 已装，vite.config.ts 的 test.coverage 段配 include 仅 src/utils/*.ts），行/语句/函数覆盖 100%、分支 97.36%。已知 provider 特性：`a || b` 的 falsy 分支即使用例已执行且断言通过，v8 仍可能计数为 0（如 fieldRender.ts:9、fieldValidation.ts:13、menuTree.ts:36），属误报不再补测。新增前端改动后跑该套件 + `npx tsc --noEmit` + `npm run build` 回归。
